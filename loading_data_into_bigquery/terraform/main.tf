provider "google" {
  project = var.project_id
}

resource "google_project_service" "bigquery" {
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_bigquery_dataset" "demo" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Pandas public data demo"
  description                = "Temporary dataset created by Terraform for a data loading demo."
  location                   = var.location
  delete_contents_on_destroy = true

  depends_on = [google_project_service.bigquery]
}

resource "google_bigquery_table" "tips" {
  dataset_id          = google_bigquery_dataset.demo.dataset_id
  table_id            = var.table_id
  deletion_protection = false

  schema = jsonencode([
    {
      name = "total_bill"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "tip"
      type = "FLOAT"
      mode = "NULLABLE"
    },
    {
      name = "sex"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "smoker"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "day"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "time"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "size"
      type = "INTEGER"
      mode = "NULLABLE"
    }
  ])
}