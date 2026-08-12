#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-us-central1}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: GCP_PROJECT_ID=your-project-id ./run.sh"
  echo "   or: ./run.sh your-project-id"
  exit 1
fi

for command_name in curl python3 terraform; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "Python venv support is required." >&2
  exit 1
fi

OPERATOR_IP="$(curl --fail --silent --show-error https://api.ipify.org)"
if [[ ! "$OPERATOR_IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
  echo "Could not determine a valid public IPv4 address." >&2
  exit 1
fi

export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_region="$REGION"
export TF_VAR_operator_cidr="${OPERATOR_IP}/32"

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

echo "Creating AlloyDB, BigQuery, and federation resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

export PGHOST="$(terraform -chdir="$TERRAFORM_DIR" output -raw alloydb_public_ip)"
export PGPASSWORD="$(terraform -chdir="$TERRAFORM_DIR" output -raw database_password)"
DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
CONNECTION_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw connection_id)"

echo "Preparing the Python environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"

echo "Seeding transactional and reference data..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/seed_data.py" \
  --project-id "$PROJECT_ID" \
  --dataset-id "$DATASET_ID"

echo "Running the BigQuery federated query..."
"$VENV_DIR/bin/python" "$ROOT_DIR/src/run_federated_query.py" \
  --project-id "$PROJECT_ID" \
  --region "$REGION" \
  --connection-id "$CONNECTION_ID" \
  --dataset-id "$DATASET_ID"

echo "Federated query completed successfully."