#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"
LOCATION="${GCP_LOCATION:-US}"
SEARCH_QUERY="${SEARCH_QUERY:-How can I build a scalable data pipeline on Google Cloud?}"

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

echo "Creating the BigQuery dataset and Vertex AI connection..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
CONNECTION_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw connection_id)"

echo "Preparing the Python environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"

echo "Generating embeddings and running semantic search..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/run_vector_search.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID" \
  --connection-id "$CONNECTION_ID" \
  --sql-directory "$ROOT_DIR/sql" \
  --query "$SEARCH_QUERY"

echo "Pipeline completed successfully."