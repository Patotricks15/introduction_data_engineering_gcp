output "bucket_name" {
  description = "Cloud Storage bucket containing the Iceberg warehouse."
  value       = google_storage_bucket.iceberg.name
}

output "dataset_id" {
  description = "BigQuery dataset containing the external table."
  value       = google_bigquery_dataset.demo.dataset_id
}

output "table_id" {
  description = "External Iceberg table ID when it has been created."
  value       = try(google_bigquery_table.tips_iceberg[0].table_id, "")
}

output "connection_id" {
  description = "BigQuery Cloud Resource connection ID."
  value       = google_bigquery_connection.iceberg.name
}