locals {
  bucket_name = "${var.project_id}-external-iceberg"
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "iceberg" {
  name                        = local.bucket_name
  location                    = var.location
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_dataset" "demo" {
  dataset_id                 = var.dataset_id
  friendly_name              = "External Iceberg Demo"
  description                = "BigQuery external table over an Apache Iceberg table in Cloud Storage."
  location                   = var.location
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_connection" "iceberg" {
  connection_id = "iceberg-cloud-resource"
  location      = var.location
  friendly_name = "Iceberg Cloud Resource connection"
  description   = "Delegates BigQuery reads of Iceberg metadata and Parquet files."

  cloud_resource {}

  depends_on = [google_project_service.services]
}

resource "google_storage_bucket_iam_member" "connection_reader" {
  bucket = google_storage_bucket.iceberg.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.iceberg.cloud_resource[0].service_account_id}"
}

resource "google_bigquery_table" "tips_iceberg" {
  count = var.iceberg_metadata_uri == "" ? 0 : 1

  dataset_id          = google_bigquery_dataset.demo.dataset_id
  table_id            = "tips_iceberg"
  description         = "External BigQuery table backed by Apache Iceberg metadata and Parquet files."
  deletion_protection = false

  external_data_configuration {
    autodetect    = true
    connection_id = google_bigquery_connection.iceberg.name
    source_format = "ICEBERG"
    source_uris   = [var.iceberg_metadata_uri]
  }

  depends_on = [google_storage_bucket_iam_member.connection_reader]
}