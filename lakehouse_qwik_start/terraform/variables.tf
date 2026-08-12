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
  description = "BigQuery, connection, and Cloud Storage location."
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset containing the Lakehouse tables."
  type        = string
  default     = "lakehouse_demo"
}

variable "create_tables" {
  description = "Create external tables after the source CSV files are uploaded."
  type        = bool
  default     = false
}