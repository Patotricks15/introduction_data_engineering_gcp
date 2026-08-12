variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for Dataflow, Cloud Storage, and BigQuery."
  type        = string
  default     = "us-central1"
}

variable "dataset_id" {
  description = "BigQuery dataset receiving streaming aggregates."
  type        = string
  default     = "traffic_streaming"
}

variable "runner_member" {
  description = "Authenticated identity allowed to launch Dataflow with the worker service account."
  type        = string
}