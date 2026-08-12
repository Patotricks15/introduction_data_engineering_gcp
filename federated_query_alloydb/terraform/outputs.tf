output "alloydb_public_ip" {
  description = "Public endpoint used only to initialize the demo database."
  value       = google_alloydb_instance.primary.public_ip_address
}

output "database_password" {
  description = "Generated password for the demo AlloyDB user."
  value       = random_password.database.result
  sensitive   = true
}

output "dataset_id" {
  description = "BigQuery dataset containing native reference data."
  value       = google_bigquery_dataset.analytics.dataset_id
}

output "connection_id" {
  description = "Short BigQuery AlloyDB connection ID."
  value       = google_bigquery_connection.alloydb.connection_id
}

output "connection_name" {
  description = "Fully qualified BigQuery AlloyDB connection name."
  value       = "${var.project_id}.${var.region}.${google_bigquery_connection.alloydb.connection_id}"
}