#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
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

export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_region="$REGION"
export TF_VAR_location="$LOCATION"

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

echo "Creating the Dataform repository and BigQuery datasets..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
REPOSITORY_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw repository_id)"
SERVICE_ACCOUNT="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataform_service_account)"

echo "Preparing the Python environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"

echo "Publishing, compiling, and executing the SQL workflow..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/run_workflow.py" \
  --project-id "$PROJECT_ID" \
  --region "$REGION" \
  --repository-id "$REPOSITORY_ID" \
  --dataset-id "$DATASET_ID" \
  --service-account "$SERVICE_ACCOUNT" \
  --source-directory "$ROOT_DIR/dataform"

echo "Pipeline completed successfully."