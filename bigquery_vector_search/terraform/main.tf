resource "google_project_service" "services" {
  for_each = toset([
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_bigquery_dataset" "vector_search" {
  dataset_id                 = var.dataset_id
  friendly_name              = "BigQuery Vector Search Demo"
  description                = "Documents and embeddings used for semantic similarity search."
  location                   = var.location
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_connection" "vertex_ai" {
  connection_id = var.connection_id
  location      = var.location
  friendly_name = "Vertex AI embedding connection"
  description   = "Delegates embedding generation from BigQuery to Vertex AI."

  cloud_resource {}

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "connection_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_bigquery_connection.vertex_ai.cloud_resource[0].service_account_id}"
}