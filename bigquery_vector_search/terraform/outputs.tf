output "dataset_id" {
  description = "BigQuery dataset used by the vector search workflow."
  value       = google_bigquery_dataset.vector_search.dataset_id
}

output "connection_id" {
  description = "Fully qualified BigQuery connection name."
  value       = google_bigquery_connection.vertex_ai.name
}

output "connection_service_account" {
  description = "Managed identity used to invoke Vertex AI."
  value       = google_bigquery_connection.vertex_ai.cloud_resource[0].service_account_id
}