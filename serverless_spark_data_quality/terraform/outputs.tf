output "bucket_name" {
  description = "Cloud Storage bucket for batch input and Spark dependencies."
  value       = google_storage_bucket.pipeline.name
}

output "dataset_id" {
  description = "BigQuery dataset receiving quality-assessed output."
  value       = google_bigquery_dataset.quality.dataset_id
}

output "spark_service_account" {
  description = "Service account used by Serverless Spark batches."
  value       = google_service_account.spark.email
}

output "valid_table_id" {
  description = "BigQuery table containing records that passed every rule."
  value       = "valid_orders"
}

output "rejected_table_id" {
  description = "BigQuery table containing records and their failed rules."
  value       = "rejected_orders"
}

output "metrics_table_id" {
  description = "BigQuery table containing aggregate quality metrics."
  value       = "quality_metrics"
}