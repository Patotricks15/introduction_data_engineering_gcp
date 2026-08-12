#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
WORK_DIR="$ROOT_DIR/.work"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"
LOCATION="${GCP_LOCATION:-US}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: GCP_PROJECT_ID=your-project-id ./run.sh"
  echo "   or: ./run.sh your-project-id"
  exit 1
fi

for command_name in terraform python3; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "Python's venv support is required." >&2
  exit 1
fi

mkdir -p "$WORK_DIR"
export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_region="$REGION"
export TF_VAR_location="$LOCATION"
export TF_VAR_iceberg_metadata_uri=""

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

echo "Creating the Cloud Storage warehouse, BigQuery dataset, and connection..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw bucket_name)"
DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"

echo "Preparing the Python environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"

echo "Writing the public Tips dataset as an Apache Iceberg table..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/prepare_iceberg.py" \
  --project-id "$PROJECT_ID" \
  --bucket-name "$BUCKET_NAME" \
  --catalog-path "$WORK_DIR/catalog.db" \
  --output "$WORK_DIR/iceberg-table.json"

export TF_VAR_iceberg_metadata_uri
TF_VAR_iceberg_metadata_uri="$(
  "$VENV_DIR/bin/python" -c \
    'import json,sys; print(json.load(open(sys.argv[1]))["metadata_location"])' \
    "$WORK_DIR/iceberg-table.json"
)"

echo "Registering the Iceberg metadata as a BigQuery external table..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false
TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw table_id)"

echo "Querying the external Iceberg table from BigQuery..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/verify_iceberg.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID" \
  --table-id "$TABLE_ID"

echo "Pipeline completed successfully."