variable "project_id" {
  description = "GCP project where the BigQuery resources are created."
  type        = string

  validation {
    condition     = length(var.project_id) > 0
    error_message = "project_id must not be empty."
  }
}

variable "location" {
  description = "BigQuery dataset location."
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset ID."
  type        = string
  default     = "pandas_demo"

  validation {
    condition     = can(regex("^[A-Za-z_][A-Za-z0-9_]*$", var.dataset_id))
    error_message = "dataset_id must contain only letters, numbers, and underscores."
  }
}

variable "table_id" {
  description = "BigQuery table ID."
  type        = string
  default     = "tips"

  validation {
    condition     = can(regex("^[A-Za-z_][A-Za-z0-9_]*$", var.table_id))
    error_message = "table_id must contain only letters, numbers, and underscores."
  }
}