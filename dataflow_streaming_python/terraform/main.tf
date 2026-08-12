locals {
  bucket_name = "${var.project_id}-dataflow-streaming-python"
  aggregate_schema = [
    { name = "window_start", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "window_end", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "corridor", type = "STRING", mode = "REQUIRED" },
    { name = "vehicle_count", type = "INTEGER", mode = "REQUIRED" },
    { name = "average_speed_kph", type = "FLOAT", mode = "REQUIRED" },
    { name = "max_speed_kph", type = "INTEGER", mode = "REQUIRED" },
  ]
  error_schema = [
    { name = "payload", type = "STRING", mode = "REQUIRED" },
    { name = "error", type = "STRING", mode = "REQUIRED" },
    { name = "failed_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ]
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "compute.googleapis.com",
    "dataflow.googleapis.com",
    "iam.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_pubsub_topic" "traffic" {
  name = "traffic-events"

  depends_on = [google_project_service.services]
}

resource "google_storage_bucket" "dataflow" {
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_dataset" "streaming" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Python Dataflow Streaming"
  description                = "Windowed traffic aggregates produced by Apache Beam."
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table" "aggregates" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "corridor_metrics"
  description         = "Per-corridor traffic metrics computed in fixed event-time windows."
  deletion_protection = false
  schema              = jsonencode(local.aggregate_schema)

  time_partitioning {
    type  = "DAY"
    field = "window_start"
  }

  clustering = ["corridor"]
}

resource "google_bigquery_table" "errors" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "dead_letter_events"
  description         = "Streaming payloads rejected by event validation."
  deletion_protection = false
  schema              = jsonencode(local.error_schema)
}

resource "google_service_account" "dataflow" {
  account_id   = "traffic-dataflow-worker"
  display_name = "Python traffic streaming worker"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "dataflow_roles" {
  for_each = toset([
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/dataflow.worker",
    "roles/pubsub.subscriber",
    "roles/storage.objectAdmin",
  ])

  project = var.project_id
  role    = each.value
  member  = google_service_account.dataflow.member
}

resource "google_service_account_iam_member" "runner_can_act_as" {
  service_account_id = google_service_account.dataflow.name
  role               = "roles/iam.serviceAccountUser"
  member             = var.runner_member
}