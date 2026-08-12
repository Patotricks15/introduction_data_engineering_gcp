variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Google Cloud region used by regional resources."
  type        = string
  default     = "us-central1"
}

variable "location" {
  description = "BigQuery and Cloud Storage location."
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset containing the external Iceberg table."
  type        = string
  default     = "external_iceberg"
}

variable "iceberg_metadata_uri" {
  description = "Cloud Storage URI of the current Iceberg metadata JSON file."
  type        = string
  default     = ""
}