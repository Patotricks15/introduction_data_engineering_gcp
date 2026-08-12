locals {
  bucket_name = "${var.project_id}-spark-data-quality"
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
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

resource "google_bigquery_dataset" "quality" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Serverless Spark Data Quality"
  description                = "Valid orders, rejected records, and quality metrics from a Spark batch."
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_service_account" "spark" {
  account_id   = "spark-quality-runner"
  display_name = "Serverless Spark data quality runner"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "spark_roles" {
  for_each = toset([
    "roles/bigquery.jobUser",
    "roles/dataproc.worker",
  ])

  project = var.project_id
  role    = each.value
  member  = google_service_account.spark.member
}

resource "google_storage_bucket_iam_member" "spark_bucket_access" {
  bucket = google_storage_bucket.pipeline.name
  role   = "roles/storage.objectAdmin"
  member = google_service_account.spark.member
}

resource "google_bigquery_dataset_iam_member" "spark_dataset_access" {
  dataset_id = google_bigquery_dataset.quality.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.spark.member
}

resource "google_service_account_iam_member" "runner_can_act_as" {
  service_account_id = google_service_account.spark.name
  role               = "roles/iam.serviceAccountUser"
  member             = var.runner_member
}