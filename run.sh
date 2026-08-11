#!/usr/bin/env bash
# Template run.sh for GCP data engineering projects.
# Copy this file into your project folder and adapt the pipeline section.
#
# Usage:
#   GCP_PROJECT_ID=your-project-id ./run.sh
#   ./run.sh your-project-id

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$ROOT_DIR/terraform"
VENV_DIR="$ROOT_DIR/.venv"
PROJECT_ID="${GCP_PROJECT_ID:-${1:-}}"
REGION="${GCP_REGION:-southamerica-east1}"

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: GCP_PROJECT_ID=your-project-id ./run.sh"
  echo "   or: ./run.sh your-project-id"
  exit 1
fi

for cmd in terraform python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Required command not found: $cmd" >&2
    exit 1
  fi
done

# ---------------------------------------------------------------------------
# Terraform environment
# ---------------------------------------------------------------------------

export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_region="$REGION"

echo "Initializing Terraform..."
terraform -chdir="$TERRAFORM_DIR" init -input=false

# ---------------------------------------------------------------------------
# Cleanup trap — always destroys resources on exit or failure
# ---------------------------------------------------------------------------

cleanup() {
  local exit_status=$?
  trap - EXIT
  set +e

  echo
  echo "Destroying GCP resources..."
  terraform -chdir="$TERRAFORM_DIR" destroy -auto-approve -input=false
  local destroy_status=$?

  [[ $exit_status -ne 0 ]] && exit "$exit_status"
  exit "$destroy_status"
}

trap cleanup EXIT

# ---------------------------------------------------------------------------
# Provision
# ---------------------------------------------------------------------------

echo "Creating GCP resources..."
terraform -chdir="$TERRAFORM_DIR" apply -auto-approve -input=false

# ---------------------------------------------------------------------------
# Pipeline
# Adapt this section for each project.
# Examples:
#   - Read terraform outputs and pass them to your Python script
#   - Build and push a Docker image before apply when using Cloud Run
#   - Run a Cloud Run job trigger after apply
# ---------------------------------------------------------------------------

# Example: read outputs and run a Python pipeline
# DATASET_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw dataset_id)"
# TABLE_ID="$(terraform -chdir="$TERRAFORM_DIR" output -raw table_id)"
#
# echo "Preparing Python environment..."
# python3 -m venv "$VENV_DIR"
# "$VENV_DIR/bin/python" -m pip install --quiet --requirement "$ROOT_DIR/requirements.txt"
#
# echo "Running pipeline..."
# "$VENV_DIR/bin/python" "$ROOT_DIR/src/main.py" \
#   --project-id "$PROJECT_ID" \
#   --dataset-id "$DATASET_ID" \
#   --table-id "$TABLE_ID"

# Example: build and push Docker image before terraform apply (Cloud Run projects)
# REGION="${GCP_REGION:-southamerica-east1}"
# REPOSITORY="your-repo-name"
# IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/app:latest"
# export TF_VAR_collector_image="$IMAGE"
#
# gcloud auth print-access-token | \
#   docker login -u oauth2accesstoken --password-stdin "https://${REGION}-docker.pkg.dev"
#
# docker build --timeout=120 -t "$IMAGE" ./app
# docker push "$IMAGE"

echo "Pipeline completed successfully."
