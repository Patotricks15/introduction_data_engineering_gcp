output "topic_id" {
  description = "Pub/Sub topic receiving weather events."
  value       = google_pubsub_topic.weather.name
}

output "dataflow_bucket_name" {
  description = "Cloud Storage bucket used for Dataflow staging and temporary files."
  value       = google_storage_bucket.dataflow.name
}

output "dataflow_worker_email" {
  description = "Service account used by Dataflow workers."
  value       = google_service_account.dataflow_worker.email
}

output "dataset_id" {
  description = "BigQuery dataset containing raw events and dashboard views."
  value       = google_bigquery_dataset.streaming.dataset_id
}

output "table_id" {
  description = "BigQuery destination table ID."
  value       = google_bigquery_table.weather_events.table_id
}

output "latest_weather_view" {
  description = "Fully qualified latest-weather dashboard view."
  value       = "${var.project_id}.${google_bigquery_dataset.streaming.dataset_id}.${google_bigquery_table.latest_weather.table_id}"
}

output "weather_trends_view" {
  description = "Fully qualified weather-trends dashboard view."
  value       = "${var.project_id}.${google_bigquery_dataset.streaming.dataset_id}.${google_bigquery_table.weather_trends.table_id}"
}