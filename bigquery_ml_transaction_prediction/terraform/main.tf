resource "google_project_service" "bigquery" {
  project            = var.project_id
  service            = "bigquery.googleapis.com"
  disable_on_destroy = false
}

resource "google_bigquery_dataset" "ml" {
  dataset_id                 = var.dataset_id
  friendly_name              = "BigQuery ML Transaction Prediction"
  description                = "Logistic regression model and visitor transaction predictions."
  location                   = var.location
  delete_contents_on_destroy = true

  depends_on = [google_project_service.bigquery]
}