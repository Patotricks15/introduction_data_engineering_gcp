output "dataset_id" {
  description = "BigQuery dataset containing ML artifacts."
  value       = google_bigquery_dataset.ml.dataset_id
}

output "model_id" {
  description = "BigQuery ML model ID created by the pipeline."
  value       = "visitor_purchase_model"
}

output "prediction_table_id" {
  description = "BigQuery table containing scored visitors."
  value       = "visitor_predictions"
}