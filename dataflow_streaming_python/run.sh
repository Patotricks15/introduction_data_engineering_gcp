#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"
EVENT_COUNT="${EVENT_COUNT:-30}"
JOB_NAME="traffic-stream-python-$(date -u +%Y%m%d-%H%M%S)"
JOB_ID=""

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: GCP_PROJECT_ID=your-project-id ./run.sh"
  echo "   or: ./run.sh your-project-id"
  exit 1
fi

if [[ ! "$EVENT_COUNT" =~ ^[1-9][0-9]*$ ]]; then
  echo "EVENT_COUNT must be a positive integer." >&2
  exit 1
fi

for command_name in gcloud python3 terraform; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "Python venv support is required." >&2
  exit 1
fi

ACTIVE_ACCOUNT="$(gcloud config get-value account 2>/dev/null)"
if [[ -z "$ACTIVE_ACCOUNT" || "$ACTIVE_ACCOUNT" == "(unset)" ]]; then
  echo "No active gcloud account. Run: gcloud auth login" >&2
  exit 1
fi
if [[ "$ACTIVE_ACCOUNT" == *".gserviceaccount.com" ]]; then
  RUNNER_MEMBER="serviceAccount:$ACTIVE_ACCOUNT"
else
  RUNNER_MEMBER="user:$ACTIVE_ACCOUNT"
fi

export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_region="$REGION"
export TF_VAR_runner_member="$RUNNER_MEMBER"

terraform -chdir="$TERRAFORM_DIR" init -input=false

cleanup() {
  local run_status=$?
  trap - EXIT
  set +e
  if [[ -n "$JOB_ID" ]]; then
    echo
    echo "Cancelling Dataflow job $JOB_ID..."
    gcloud dataflow jobs cancel "$JOB_ID" \
      --project="$PROJECT_ID" \
      --region="$REGION" \
      --quiet
  fi
  echo
  echo "Destroying GCP resources..."
  terraform -chdir="$TERRAFORM_DIR" destroy -auto-approve -input=false
  local destroy_status=$?
  [[ $run_status -ne 0 ]] && exit "$run_status"
  exit "$destroy_status"
}

trap cleanup EXIT

echo "Creating Pub/Sub, BigQuery, and Dataflow resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

TOPIC_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw topic_id)"
BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataflow_bucket_name)"
WORKER_EMAIL="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataflow_service_account)"
DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
AGGREGATE_TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw aggregate_table_id)"
DEAD_LETTER_TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dead_letter_table_id)"

echo "Preparing Python dependencies..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"

echo "Submitting the Python Apache Beam pipeline to Dataflow..."
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/beam_pipeline.py" \
  --runner DataflowRunner \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --job_name "$JOB_NAME" \
  --temp_location "gs://$BUCKET_NAME/temp" \
  --staging_location "gs://$BUCKET_NAME/staging" \
  --service_account_email "$WORKER_EMAIL" \
  --requirements_file "$ROOT_DIR/dataflow-requirements.txt" \
  --input-topic "projects/$PROJECT_ID/topics/$TOPIC_ID" \
  --output-table "$PROJECT_ID:$DATASET_ID.$AGGREGATE_TABLE_ID" \
  --dead-letter-table "$PROJECT_ID:$DATASET_ID.$DEAD_LETTER_TABLE_ID"

for _ in {1..36}; do
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

echo "Publishing $EVENT_COUNT valid events and one invalid event..."
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/publish_events.py" \
  --project-id "$PROJECT_ID" \
  --topic-id "$TOPIC_ID" \
  --event-count "$EVENT_COUNT"

echo "Verifying windowed aggregates and dead-letter routing..."
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/verify_pipeline.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID" \
  --aggregate-table-id "$AGGREGATE_TABLE_ID" \
  --dead-letter-table-id "$DEAD_LETTER_TABLE_ID" \
  --expected-events "$EVENT_COUNT"

echo "Python streaming pipeline completed successfully."