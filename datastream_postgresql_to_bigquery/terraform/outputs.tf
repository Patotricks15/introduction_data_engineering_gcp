output "database_host" {
  description = "Public IP address of the temporary PostgreSQL source."
  value       = google_sql_database_instance.source.public_ip_address
}

output "database_name" {
  description = "PostgreSQL source database name."
  value       = google_sql_database.source.name
}

output "postgres_password" {
  description = "Temporary PostgreSQL administrator password."
  value       = random_password.postgres.result
  sensitive   = true
}

output "datastream_password" {
  description = "Temporary Datastream database user password."
  value       = random_password.datastream.result
  sensitive   = true
}

output "dataset_id" {
  description = "BigQuery destination dataset ID."
  value       = google_bigquery_dataset.replica.dataset_id
}

output "stream_id" {
  description = "Datastream stream ID when the stream is enabled."
  value       = var.create_stream ? google_datastream_stream.replication[0].stream_id : null
}