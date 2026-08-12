output "topic_id" {
  description = "Pub/Sub topic receiving traffic events."
  value       = google_pubsub_topic.traffic.name
}

output "dataflow_bucket_name" {
  description = "Cloud Storage bucket for Dataflow staging and temporary files."
  value       = google_storage_bucket.dataflow.name
}

output "dataflow_service_account" {
  description = "Service account used by Dataflow workers."
  value       = google_service_account.dataflow.email
}

output "dataset_id" {
  description = "BigQuery dataset containing streaming outputs."
  value       = google_bigquery_dataset.streaming.dataset_id
}

output "aggregate_table_id" {
  description = "BigQuery table containing windowed traffic metrics."
  value       = google_bigquery_table.aggregates.table_id
}

output "dead_letter_table_id" {
  description = "BigQuery table containing invalid payloads."
  value       = google_bigquery_table.errors.table_id
}