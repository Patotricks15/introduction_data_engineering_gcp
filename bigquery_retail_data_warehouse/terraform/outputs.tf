output "dataset_id" {
  description = "BigQuery warehouse dataset ID."
  value       = google_bigquery_dataset.warehouse.dataset_id
}