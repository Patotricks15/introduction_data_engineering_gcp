locals {
  bucket_name = "${var.project_id}-dataflow-batch-python"
}

resource "google_project_service" "services" {
  for_each = toset([
    "compute.googleapis.com",
    "dataflow.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "pipeline" {
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.services]
}

resource "google_service_account" "dataflow" {
  account_id   = "dataflow-batch-python"
  display_name = "Python batch analytics Dataflow worker"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "dataflow_worker" {
  project = var.project_id
  role    = "roles/dataflow.worker"
  member  = google_service_account.dataflow.member
}

resource "google_storage_bucket_iam_member" "worker_bucket_access" {
  bucket = google_storage_bucket.pipeline.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.dataflow.member
}

resource "google_service_account_iam_member" "runner_can_act_as" {
  service_account_id = google_service_account.dataflow.name
  role               = "roles/iam.serviceAccountUser"
  member             = var.runner_member
}