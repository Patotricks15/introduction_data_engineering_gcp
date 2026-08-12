variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for the Cloud Run function and storage buckets."
  type        = string
  default     = "us-central1"
}

variable "location" {
  description = "BigQuery dataset location."
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset receiving function loads."
  type        = string
  default     = "cloud_run_function_demo"
}

variable "table_id" {
  description = "BigQuery destination table ID."
  type        = string
  default     = "tips"
}