output "bucket_name" {
  description = "Cloud Storage bucket containing input, output, staging, and temporary files."
  value       = google_storage_bucket.pipeline.name
}

output "dataflow_service_account" {
  description = "Service account used by Dataflow workers."
  value       = google_service_account.dataflow.email
}