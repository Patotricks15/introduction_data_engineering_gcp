variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Google Cloud region used by Dataform."
  type        = string
  default     = "us-central1"
}

variable "location" {
  description = "BigQuery dataset location."
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset containing Dataform output tables."
  type        = string
  default     = "dataform_demo"
}

variable "repository_id" {
  description = "Dataform repository ID."
  type        = string
  default     = "sql-workflow"
}