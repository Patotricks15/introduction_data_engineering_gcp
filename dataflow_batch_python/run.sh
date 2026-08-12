#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
WORK_DIR="$ROOT_DIR/.work"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"
JOB_NAME="site-traffic-batch-$(date -u +%Y%m%d-%H%M%S)"

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
export TF_VAR_runner_member="$RUNNER_MEMBER"

terraform -chdir="$TERRAFORM_DIR" init -input=false

cleanup() {
  local run_status=$?
  trap - EXIT
  set +e
  echo
  echo "Destroying GCP resources..."
  terraform -chdir="$TERRAFORM_DIR" destroy -auto-approve -input=false
  local destroy_status=$?
  rm -rf "$WORK_DIR"
  [[ $run_status -ne 0 ]] && exit "$run_status"
  exit "$destroy_status"
}

trap cleanup EXIT

echo "Creating Dataflow batch resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw bucket_name)"
WORKER_EMAIL="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataflow_service_account)"

echo "Preparing Python dependencies and site traffic input..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/prepare_data.py" \
  --project-id "$PROJECT_ID" \
  --bucket-name "$BUCKET_NAME" \
  --output "$WORK_DIR/site-traffic.jsonl" \
  --event-count 120

echo "Running both Python batch aggregations on Dataflow..."
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/batch_pipeline.py" \
  --runner DataflowRunner \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --job_name "$JOB_NAME" \
  --temp_location "gs://$BUCKET_NAME/temp" \
  --staging_location "gs://$BUCKET_NAME/staging" \
  --service_account_email "$WORKER_EMAIL" \
  --input "gs://$BUCKET_NAME/input/site-traffic.jsonl" \
  --user-output "gs://$BUCKET_NAME/output/by-user/part" \
  --minute-output "gs://$BUCKET_NAME/output/by-minute/part"

echo "Verifying user and minute output shards..."
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/verify_outputs.py" \
  --project-id "$PROJECT_ID" \
  --bucket-name "$BUCKET_NAME"

echo "Both batch analytics pipelines completed successfully."