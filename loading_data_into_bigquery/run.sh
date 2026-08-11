#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
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
  echo "Python's venv support is required. Install the venv package for your Python version." >&2
  exit 1
fi

export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_location="$LOCATION"

echo "Initializing Terraform..."
terraform -chdir="$TERRAFORM_DIR" init -input=false

cleanup() {
  local run_status=$?
  trap - EXIT
  set +e

  echo
  echo "Destroying GCP resources..."
  terraform -chdir="$TERRAFORM_DIR" destroy -auto-approve -input=false
  local destroy_status=$?

  if [[ $run_status -ne 0 ]]; then
    exit "$run_status"
  fi

  exit "$destroy_status"
}

trap cleanup EXIT

echo "Creating GCP resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw table_id)"

echo "Preparing the Python environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"

echo "Loading public data into BigQuery..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/load_data.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID" \
  --table-id "$TABLE_ID" \
  --csv-path "$ROOT_DIR/data/tips.csv"

echo "Pipeline completed successfully."