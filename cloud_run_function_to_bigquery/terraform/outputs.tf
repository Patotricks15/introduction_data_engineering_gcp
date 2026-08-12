output "landing_bucket_name" {
  description = "Bucket whose CSV uploads trigger the function."
  value       = google_storage_bucket.landing.name
}

output "dataset_id" {
  description = "BigQuery destination dataset ID."
  value       = google_bigquery_dataset.demo.dataset_id
}

output "table_id" {
  description = "BigQuery destination table ID."
  value       = google_bigquery_table.tips.table_id
}

output "function_name" {
  description = "Deployed Cloud Run function name."
  value       = google_cloudfunctions2_function.loader.name
}