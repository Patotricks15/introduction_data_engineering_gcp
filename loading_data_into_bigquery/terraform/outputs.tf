output "dataset_id" {
  description = "Created BigQuery dataset ID."
  value       = google_bigquery_dataset.demo.dataset_id
}

output "table_id" {
  description = "Created BigQuery table ID."
  value       = google_bigquery_table.tips.table_id
}