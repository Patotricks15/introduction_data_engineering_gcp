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

echo "Creating Serverless Spark data-quality resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw bucket_name)"
DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
VALID_TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw valid_table_id)"
REJECTED_TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw rejected_table_id)"
METRICS_TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw metrics_table_id)"
SPARK_SERVICE_ACCOUNT="$(terraform -chdir="$TERRAFORM_DIR" output -raw spark_service_account)"

echo "Preparing and uploading the deterministic order batch..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"
"$VENV_DIR/bin/python" "$ROOT_DIR/src/prepare_data.py" \
  --project-id "$PROJECT_ID" \
  --bucket-name "$BUCKET_NAME" \
  --output "$DATA_DIR/orders.csv"

echo "Submitting the data-quality Serverless Spark batch..."
gcloud dataproc batches submit pyspark "$ROOT_DIR/src/validate_orders.py" \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --service-account="$SPARK_SERVICE_ACCOUNT" \
  --deps-bucket="$BUCKET_NAME" \
  -- \
  --input-uri="gs://$BUCKET_NAME/input/orders.csv" \
  --valid-table="$PROJECT_ID:$DATASET_ID.$VALID_TABLE_ID" \
  --rejected-table="$PROJECT_ID:$DATASET_ID.$REJECTED_TABLE_ID" \
  --metrics-table="$PROJECT_ID:$DATASET_ID.$METRICS_TABLE_ID" \
  --temporary-bucket="$BUCKET_NAME"

echo "Verifying valid, rejected, and metric outputs..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/verify_quality.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID"

echo "Pipeline completed successfully."