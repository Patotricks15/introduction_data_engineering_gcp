output "raw_bucket_name" {
  description = "Cloud Storage raw-zone bucket name."
  value       = google_storage_bucket.raw.name
}

output "sales_dataset_id" {
  description = "Sales domain BigQuery dataset ID."
  value       = google_bigquery_dataset.domains["sales"].dataset_id
}

output "customers_dataset_id" {
  description = "Customers domain BigQuery dataset ID."
  value       = google_bigquery_dataset.domains["customers"].dataset_id
}

output "orders_scan_id" {
  description = "Fully qualified orders data quality scan ID."
  value       = google_dataplex_datascan.orders_quality.name
}

output "customers_scan_id" {
  description = "Fully qualified customer data quality scan ID."
  value       = google_dataplex_datascan.customers_quality.name
}

output "quality_service_account" {
  description = "Service account used by Dataplex quality scans."
  value       = google_service_account.quality.email
}

output "catalog_entries" {
  description = "Exact Knowledge Catalog entry resource names keyed by domain."
  value       = { for domain, entry in google_dataplex_entry.domain_products : domain => entry.name }
}

output "data_products" {
  description = "Exact Dataplex data product resource names keyed by domain."
  value       = { for domain, product in google_dataplex_data_product.domains : domain => product.name }
}