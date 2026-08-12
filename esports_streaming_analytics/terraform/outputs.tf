output "topic_id" {
  description = "Pub/Sub topic receiving gameplay and chat events."
  value       = google_pubsub_topic.events.name
}

output "dataflow_bucket_name" {
  description = "Cloud Storage bucket for Dataflow staging and temporary files."
  value       = google_storage_bucket.dataflow.name
}

output "dataflow_service_account" {
  description = "Service account used by Apache Beam workers."
  value       = google_service_account.dataflow.email
}

output "bigtable_instance_id" {
  description = "Bigtable instance containing player profiles."
  value       = google_bigtable_instance.profiles.name
}

output "bigtable_table_id" {
  description = "Bigtable player profile table."
  value       = google_bigtable_table.players.name
}

output "dataset_id" {
  description = "BigQuery dataset containing events and monitoring views."
  value       = google_bigquery_dataset.streaming.dataset_id
}

output "events_table_id" {
  description = "Enriched event table."
  value       = google_bigquery_table.events.table_id
}

output "dead_letter_table_id" {
  description = "Invalid event table."
  value       = google_bigquery_table.errors.table_id
}