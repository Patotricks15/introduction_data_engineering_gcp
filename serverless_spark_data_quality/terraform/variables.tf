variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for Serverless Spark, Cloud Storage, and BigQuery."
  type        = string
  default     = "us-central1"
}

variable "dataset_id" {
  description = "BigQuery dataset containing quality-assessed output."
  type        = string
  default     = "batch_data_quality"
}

variable "runner_member" {
  description = "Authenticated user or service account allowed to submit as the Spark identity."
  type        = string
}