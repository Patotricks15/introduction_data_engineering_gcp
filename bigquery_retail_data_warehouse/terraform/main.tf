resource "google_project_service" "bigquery" {
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_bigquery_dataset" "warehouse" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Retail Data Warehouse"
  description                = "Nested raw data, conformed dimensions, partitioned facts, and reporting marts."
  location                   = var.location
  delete_contents_on_destroy = true

  labels = {
    environment = "demo"
    workload    = "data-warehouse"
  }

  depends_on = [google_project_service.bigquery]
}