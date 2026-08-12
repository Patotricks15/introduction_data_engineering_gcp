#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
WORK_DIR="$ROOT_DIR/.work"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"
ZONE="${GCP_ZONE:-us-central1-a}"
EVENT_COUNT="${EVENT_COUNT:-30}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"
DASHBOARD_SECONDS="${DASHBOARD_SECONDS:-60}"
JOB_NAME="esports-stream-$(date -u +%Y%m%d-%H%M%S)"
JOB_ID=""
DASHBOARD_PID=""

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: GCP_PROJECT_ID=your-project-id ./run.sh"
  echo "   or: ./run.sh your-project-id"
  exit 1
fi

for command_name in gcloud terraform python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "Python's venv support is required." >&2
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

mkdir -p "$WORK_DIR"
export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_region="$REGION"
export TF_VAR_zone="$ZONE"
export TF_VAR_runner_member="$RUNNER_MEMBER"

terraform -chdir="$TERRAFORM_DIR" init -input=false

cleanup() {
  local run_status=$?
  trap - EXIT
  set +e
  if [[ -n "$DASHBOARD_PID" ]]; then
    kill "$DASHBOARD_PID" 2>/dev/null || true
  fi
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
  rm -rf "$WORK_DIR"
  [[ $run_status -ne 0 ]] && exit "$run_status"
  exit "$destroy_status"
}

trap cleanup EXIT

echo "Creating Pub/Sub, Bigtable, BigQuery, and Dataflow resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

TOPIC_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw topic_id)"
BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataflow_bucket_name)"
WORKER_EMAIL="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataflow_service_account)"
BIGTABLE_INSTANCE="$(terraform -chdir="$TERRAFORM_DIR" output -raw bigtable_instance_id)"
BIGTABLE_TABLE="$(terraform -chdir="$TERRAFORM_DIR" output -raw bigtable_table_id)"
DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
EVENTS_TABLE="$(terraform -chdir="$TERRAFORM_DIR" output -raw events_table_id)"
DEAD_LETTER_TABLE="$(terraform -chdir="$TERRAFORM_DIR" output -raw dead_letter_table_id)"

echo "Preparing Python dependencies and Bigtable player profiles..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/seed_bigtable.py" \
  --project-id "$PROJECT_ID" \
  --instance-id "$BIGTABLE_INSTANCE" \
  --table-id "$BIGTABLE_TABLE"

echo "Submitting the Apache Beam streaming pipeline to Dataflow..."
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
  --output-table "$PROJECT_ID:$DATASET_ID.$EVENTS_TABLE" \
  --dead-letter-table "$PROJECT_ID:$DATASET_ID.$DEAD_LETTER_TABLE" \
  --bigtable-project "$PROJECT_ID" \
  --bigtable-instance "$BIGTABLE_INSTANCE" \
  --bigtable-table "$BIGTABLE_TABLE"

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

echo "Publishing $EVENT_COUNT gameplay and chat events..."
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/publish_events.py" \
  --project-id "$PROJECT_ID" \
  --topic-id "$TOPIC_ID" \
  --event-count "$EVENT_COUNT"

echo "Verifying Bigtable enrichment and BigQuery delivery..."
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/verify_pipeline.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID" \
  --table-id "$EVENTS_TABLE" \
  --expected-count "$EVENT_COUNT"

if [[ "$DASHBOARD_SECONDS" -gt 0 ]]; then
  echo "Starting Streamlit monitoring at http://localhost:$DASHBOARD_PORT"
  GCP_PROJECT_ID="$PROJECT_ID" GCP_DATASET_ID="$DATASET_ID" \
    "$VENV_DIR/bin/streamlit" run "$ROOT_DIR/app/dashboard.py" \
      --server.headless=true \
      --server.address=0.0.0.0 \
      --server.port="$DASHBOARD_PORT" \
      >"$WORK_DIR/streamlit.log" 2>&1 &
  DASHBOARD_PID=$!
  sleep "$DASHBOARD_SECONDS"
fi

echo "All four e-sports streaming lab scenarios completed successfully."