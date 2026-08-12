variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for Cloud Data Fusion and supporting resources."
  type        = string
  default     = "us-central1"
}

variable "dataset_id" {
  description = "BigQuery dataset receiving the curated batch."
  type        = string
  default     = "data_fusion_demo"
}