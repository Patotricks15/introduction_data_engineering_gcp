output "dataset_id" {
  description = "BigQuery dataset containing workflow outputs."
  value       = google_bigquery_dataset.workflow.dataset_id
}

output "repository_id" {
  description = "Dataform repository ID."
  value       = google_dataform_repository.workflow.name
}

output "repository_name" {
  description = "Fully qualified Dataform repository resource name."
  value       = google_dataform_repository.workflow.id
}

output "dataform_service_account" {
  description = "Service account used by Dataform workflow invocations."
  value       = google_project_service_identity.dataform.email
}