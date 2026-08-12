output "bucket_name" {
  description = "Cloud Storage data lake bucket."
  value       = google_storage_bucket.data_lake.name
}

output "connection_id" {
  description = "Fully qualified BigQuery connection ID."
  value       = google_bigquery_connection.lakehouse.name
}

output "connection_service_account" {
  description = "Service account used by BigQuery to read the data lake."
  value       = google_bigquery_connection.lakehouse.cloud_resource[0].service_account_id
}

output "dataset_id" {
  description = "BigQuery dataset containing the Lakehouse tables."
  value       = google_bigquery_dataset.demo.dataset_id
}

output "customer_table_id" {
  description = "Customer BigLake table ID."
  value       = "customers_biglake"
}

output "invoice_table_id" {
  description = "Invoice BigLake table ID."
  value       = "invoices_biglake"
}