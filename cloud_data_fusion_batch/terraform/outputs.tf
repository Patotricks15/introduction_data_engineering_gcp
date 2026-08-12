output "bucket_name" {
  description = "Cloud Storage bucket for source and temporary pipeline data."
  value       = google_storage_bucket.pipeline.name
}

output "dataset_id" {
  description = "BigQuery dataset receiving the pipeline output."
  value       = google_bigquery_dataset.pipeline.dataset_id
}

output "table_id" {
  description = "BigQuery table created by the Data Fusion sink."
  value       = "tips_curated"
}

output "data_fusion_instance_name" {
  description = "Cloud Data Fusion instance name."
  value       = google_data_fusion_instance.pipeline.name
}

output "data_fusion_api_endpoint" {
  description = "CDAP API endpoint used to deploy and execute the pipeline."
  value       = google_data_fusion_instance.pipeline.api_endpoint
}