#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"
LOCATION="${GCP_LOCATION:-US}"
PUBLISH_CYCLES="${PUBLISH_CYCLES:-3}"
PUBLISH_INTERVAL="${PUBLISH_INTERVAL:-20}"
JOB_NAME="weather-stream-$(date -u +%Y%m%d-%H%M%S)"
JOB_ID=""

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: GCP_PROJECT_ID=your-project-id ./run.sh"
  echo "   or: ./run.sh your-project-id"
  exit 1
fi

for command_name in terraform python3 gcloud; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "Python's venv support is required." >&2
  exit 1
fi

export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_region="$REGION"
export TF_VAR_location="$LOCATION"

terraform -chdir="$TERRAFORM_DIR" init -input=false

cleanup() {
  local run_status=$?
  trap - EXIT
  set +e
  if [[ -n "$JOB_ID" ]]; then
    echo
    echo "Cancelling Dataflow job $JOB_ID..."
    gcloud dataflow jobs cancel "$JOB_ID" --project="$PROJECT_ID" --region="$REGION" --quiet
  fi
  echo
  echo "Destroying GCP resources..."
  terraform -chdir="$TERRAFORM_DIR" destroy -auto-approve -input=false
  local destroy_status=$?
  [[ $run_status -ne 0 ]] && exit "$run_status"
  exit "$destroy_status"
}

trap cleanup EXIT

echo "Creating streaming resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

TOPIC_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw topic_id)"
BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataflow_bucket_name)"
WORKER_EMAIL="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataflow_worker_email)"
DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw table_id)"

echo "Preparing the Python environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"

echo "Starting the Pub/Sub to BigQuery Dataflow template..."
gcloud dataflow jobs run "$JOB_NAME" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --gcs-location="gs://dataflow-templates-$REGION/latest/PubSub_to_BigQuery" \
  --staging-location="gs://$BUCKET_NAME/staging" \
  --service-account-email="$WORKER_EMAIL" \
  --parameters="inputTopic=projects/$PROJECT_ID/topics/$TOPIC_ID,outputTableSpec=$PROJECT_ID:$DATASET_ID.$TABLE_ID"

for _ in {1..30}; do
  JOB_ID="$(gcloud dataflow jobs list \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --filter="name=$JOB_NAME AND state=Running" \
    --format="value(id)" \
    --limit=1)"
  [[ -n "$JOB_ID" ]] && break
  sleep 10
done

if [[ -z "$JOB_ID" ]]; then
  echo "Dataflow job did not reach the Running state." >&2
  exit 1
fi

echo "Publishing live Open-Meteo observations..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/publish_weather.py" \
  --project-id "$PROJECT_ID" \
  --topic-id "$TOPIC_ID" \
  --cycles "$PUBLISH_CYCLES" \
  --interval "$PUBLISH_INTERVAL"

EXPECTED_ROWS=$((PUBLISH_CYCLES * 5))
echo "Waiting for at least $EXPECTED_ROWS rows in BigQuery..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/verify_pipeline.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID" \
  --table-id "$TABLE_ID" \
  --minimum-rows "$EXPECTED_ROWS"

echo "Pipeline completed successfully. Dashboard views are ready in $DATASET_ID."