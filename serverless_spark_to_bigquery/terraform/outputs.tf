output "bucket_name" {
  description = "Cloud Storage bucket used for source data and temporary files."
  value       = google_storage_bucket.pipeline.name
}

output "dataset_id" {
  description = "BigQuery dataset receiving the Spark output."
  value       = google_bigquery_dataset.pipeline.dataset_id
}

output "spark_service_account" {
  description = "Service account used by the Serverless Spark batch."
  value       = google_service_account.spark.email
}

output "table_id" {
  description = "BigQuery table written by the Spark template."
  value       = "tips"
}