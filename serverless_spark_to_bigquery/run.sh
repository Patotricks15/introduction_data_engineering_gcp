#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
DATA_DIR="$ROOT_DIR/data"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"

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
  echo
  echo "Destroying GCP resources..."
  terraform -chdir="$TERRAFORM_DIR" destroy -auto-approve -input=false
  local destroy_status=$?
  [[ $run_status -ne 0 ]] && exit "$run_status"
  exit "$destroy_status"
}

trap cleanup EXIT

echo "Creating Serverless Spark resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw bucket_name)"
DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw table_id)"
SPARK_SERVICE_ACCOUNT="$(terraform -chdir="$TERRAFORM_DIR" output -raw spark_service_account)"

echo "Preparing the Python environment and public dataset..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"
"$VENV_DIR/bin/python" "$ROOT_DIR/src/prepare_data.py" \
  --project-id "$PROJECT_ID" \
  --bucket-name "$BUCKET_NAME" \
  --output "$DATA_DIR/tips.csv"

echo "Submitting the GCS-to-BigQuery Serverless Spark template..."
gcloud dataproc batches submit pyspark "$ROOT_DIR/src/gcs_to_bigquery.py" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --service-account="$SPARK_SERVICE_ACCOUNT" \
  --deps-bucket="$BUCKET_NAME" \
  -- \
  --input-uri="gs://$BUCKET_NAME/input/tips.csv" \
  --output-table="$PROJECT_ID:$DATASET_ID.$TABLE_ID" \
  --temporary-bucket="$BUCKET_NAME"

echo "Verifying the BigQuery output..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/verify_load.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID" \
  --table-id "$TABLE_ID"

echo "Pipeline completed successfully."