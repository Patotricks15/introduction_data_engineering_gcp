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

for command_name in gcloud python3 terraform; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  echo "Python venv support is required." >&2
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
export TF_VAR_sales_steward_member="${SALES_STEWARD_MEMBER:-}"
export TF_VAR_customer_analyst_member="${CUSTOMER_ANALYST_MEMBER:-}"

terraform -chdir="$TERRAFORM_DIR" init -input=false

cleanup() {
  local run_status=$?
  trap - EXIT
  set +e
  echo
  echo "Destroying Knowledge Catalog data mesh resources..."
  terraform -chdir="$TERRAFORM_DIR" destroy -auto-approve -input=false
  local destroy_status=$?
  [[ $run_status -ne 0 ]] && exit "$run_status"
  exit "$destroy_status"
}

trap cleanup EXIT

echo "Creating the governed data mesh..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

BUCKET_NAME="$(terraform -chdir="$TERRAFORM_DIR" output -raw raw_bucket_name)"
SALES_DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw sales_dataset_id)"
CUSTOMERS_DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw customers_dataset_id)"
ORDERS_SCAN_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw orders_scan_id)"
CUSTOMERS_SCAN_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw customers_scan_id)"
CATALOG_ENTRIES="$(terraform -chdir="$TERRAFORM_DIR" output -json catalog_entries)"
DATA_PRODUCTS="$(terraform -chdir="$TERRAFORM_DIR" output -json data_products)"

echo "Preparing Python dependencies..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"

echo "Publishing domain data and running the mesh challenge..."
PYTHONPATH="$ROOT_DIR" "$VENV_DIR/bin/python" "$ROOT_DIR/src/run_mesh.py" \
  --project-id "$PROJECT_ID" \
  --region "$REGION" \
  --bucket-name "$BUCKET_NAME" \
  --sales-dataset-id "$SALES_DATASET_ID" \
  --customers-dataset-id "$CUSTOMERS_DATASET_ID" \
  --orders-scan-id "$ORDERS_SCAN_ID" \
  --customers-scan-id "$CUSTOMERS_SCAN_ID" \
  --catalog-entries "$CATALOG_ENTRIES" \
  --data-products "$DATA_PRODUCTS" \
  --data-dir "$ROOT_DIR/data"

echo "Knowledge Catalog data mesh completed successfully."