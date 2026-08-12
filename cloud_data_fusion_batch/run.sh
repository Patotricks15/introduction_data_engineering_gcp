#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
WORK_DIR="$ROOT_DIR/.work"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"
PIPELINE_NAME="${PIPELINE_NAME:-tips-batch-etl}"

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

mkdir -p "$WORK_DIR"
export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_region="$REGION"

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

echo "Creating Cloud Data Fusion resources (instance creation can take 20-30 minutes)..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw bucket_name)"
DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw table_id)"
API_ENDPOINT="$(terraform -chdir="$TERRAFORM_DIR" output -raw data_fusion_api_endpoint)"

echo "Preparing the pipeline definition and public input data..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"
"$VENV_DIR/bin/python" "$ROOT_DIR/src/build_pipeline.py" \
  --name "$PIPELINE_NAME" \
  --output "$WORK_DIR/pipeline.json"
"$VENV_DIR/bin/python" "$ROOT_DIR/src/prepare_data.py" \
  --project-id "$PROJECT_ID" \
  --bucket-name "$BUCKET_NAME" \
  --output "$WORK_DIR/tips.csv"

echo "Deploying and running the Pipeline Studio batch ETL..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/run_pipeline.py" \
  --api-endpoint "$API_ENDPOINT" \
  --pipeline "$WORK_DIR/pipeline.json" \
  --input-path "gs://$BUCKET_NAME/input/tips.csv" \
  --dataset-id "$DATASET_ID" \
  --table-id "$TABLE_ID" \
  --temporary-bucket "$BUCKET_NAME" \
  --location "$REGION"

echo "Verifying the curated BigQuery table..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/verify_output.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID" \
  --table-id "$TABLE_ID"

echo "Pipeline completed successfully."