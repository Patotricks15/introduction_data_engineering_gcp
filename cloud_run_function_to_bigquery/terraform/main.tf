locals {
  source_bucket_name  = "${var.project_id}-function-source"
  landing_bucket_name = "${var.project_id}-function-landing"
}

resource "google_project_service" "services" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "bigquery.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "eventarc.googleapis.com",
    "pubsub.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "source" {
  name                        = local.source_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.services]
}

resource "google_storage_bucket" "landing" {
  name                        = local.landing_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.services]
}

data "archive_file" "function" {
  type        = "zip"
  source_dir  = "${path.module}/../function"
  output_path = "${path.module}/function-source.zip"
}

resource "google_storage_bucket_object" "function_source" {
  name   = "function-source-${data.archive_file.function.output_md5}.zip"
  bucket = google_storage_bucket.source.name
  source = data.archive_file.function.output_path
}

resource "google_bigquery_dataset" "demo" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Cloud Run Function Load Demo"
  description                = "CSV data loaded by an event-driven Cloud Run function."
  location                   = var.location
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table" "tips" {
  dataset_id          = google_bigquery_dataset.demo.dataset_id
  table_id            = var.table_id
  description         = "Restaurant tips loaded from Cloud Storage by a Cloud Run function."
  deletion_protection = false

  schema = jsonencode([
    { name = "total_bill", type = "FLOAT", mode = "REQUIRED" },
    { name = "tip", type = "FLOAT", mode = "REQUIRED" },
    { name = "sex", type = "STRING", mode = "REQUIRED" },
    { name = "smoker", type = "STRING", mode = "REQUIRED" },
    { name = "day", type = "STRING", mode = "REQUIRED" },
    { name = "time", type = "STRING", mode = "REQUIRED" },
    { name = "size", type = "INTEGER", mode = "REQUIRED" },
  ])
}

resource "google_service_account" "function" {
  account_id   = "bq-loader-function"
  display_name = "BigQuery loader Cloud Run function"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "function_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.function.email}"
}

resource "google_bigquery_dataset_iam_member" "function_data_editor" {
  dataset_id = google_bigquery_dataset.demo.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.function.email}"
}

resource "google_storage_bucket_iam_member" "function_object_viewer" {
  bucket = google_storage_bucket.landing.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.function.email}"
}

resource "google_project_iam_member" "function_event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.function.email}"
}

data "google_storage_project_service_account" "storage" {
  project = var.project_id

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "storage_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.storage.email_address}"
}

resource "google_cloudfunctions2_function" "loader" {
  name        = "load-csv-into-bigquery"
  location    = var.region
  description = "Loads CSV objects from Cloud Storage into BigQuery."

  build_config {
    runtime     = "python312"
    entry_point = "load_csv_to_bigquery"

    source {
      storage_source {
        bucket = google_storage_bucket.source.name
        object = google_storage_bucket_object.function_source.name
      }
    }
  }

  service_config {
    available_memory      = "256M"
    timeout_seconds       = 120
    max_instance_count    = 3
    service_account_email = google_service_account.function.email

    environment_variables = {
      BIGQUERY_DATASET = google_bigquery_dataset.demo.dataset_id
      BIGQUERY_TABLE   = google_bigquery_table.tips.table_id
    }
  }

  event_trigger {
    trigger_region        = var.region
    event_type            = "google.cloud.storage.object.v1.finalized"
    retry_policy          = "RETRY_POLICY_RETRY"
    service_account_email = google_service_account.function.email

    event_filters {
      attribute = "bucket"
      value     = google_storage_bucket.landing.name
    }
  }

  depends_on = [
    google_bigquery_dataset_iam_member.function_data_editor,
    google_project_iam_member.function_event_receiver,
    google_project_iam_member.function_job_user,
    google_project_iam_member.storage_pubsub_publisher,
    google_storage_bucket_iam_member.function_object_viewer,
  ]
}