data "google_project" "current" {
  project_id = var.project_id
}

locals {
  bucket_name               = "${var.project_id}-data-fusion-batch"
  data_fusion_service_agent = "service-${data.google_project.current.number}@gcp-sa-datafusion.iam.gserviceaccount.com"
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "compute.googleapis.com",
    "datafusion.googleapis.com",
    "dataproc.googleapis.com",
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

resource "google_bigquery_dataset" "pipeline" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Cloud Data Fusion Batch Demo"
  description                = "Curated output from a Cloud Data Fusion batch ETL pipeline."
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_service_account" "data_fusion" {
  account_id   = "data-fusion-pipeline"
  display_name = "Cloud Data Fusion pipeline runtime"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "runtime_roles" {
  for_each = toset([
    "roles/bigquery.jobUser",
    "roles/dataproc.worker",
  ])

  project = var.project_id
  role    = each.value
  member  = google_service_account.data_fusion.member
}

resource "google_storage_bucket_iam_member" "runtime_bucket_access" {
  bucket = google_storage_bucket.pipeline.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.data_fusion.member
}

resource "google_bigquery_dataset_iam_member" "runtime_dataset_access" {
  dataset_id = google_bigquery_dataset.pipeline.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.data_fusion.member
}

resource "google_service_account_iam_member" "service_agent_can_act_as" {
  service_account_id = google_service_account.data_fusion.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.data_fusion_service_agent}"

  depends_on = [google_project_service.services]
}

resource "google_data_fusion_instance" "pipeline" {
  name                          = "batch-pipeline-studio"
  region                        = var.region
  type                          = "BASIC"
  enable_stackdriver_logging    = true
  enable_stackdriver_monitoring = true
  dataproc_service_account      = google_service_account.data_fusion.email

  labels = {
    workload = "batch-etl-demo"
  }

  depends_on = [
    google_project_iam_member.runtime_roles,
    google_storage_bucket_iam_member.runtime_bucket_access,
    google_bigquery_dataset_iam_member.runtime_dataset_access,
    google_service_account_iam_member.service_agent_can_act_as,
  ]
}