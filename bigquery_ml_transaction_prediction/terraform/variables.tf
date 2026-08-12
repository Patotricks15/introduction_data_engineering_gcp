variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "location" {
  description = "BigQuery dataset location."
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset containing the ML model and prediction table."
  type        = string
  default     = "bqml_ecommerce"
}