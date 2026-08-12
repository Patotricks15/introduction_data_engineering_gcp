variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for Dataflow and Cloud Storage resources."
  type        = string
  default     = "us-central1"
}

variable "location" {
  description = "Location for the BigQuery dataset."
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset for streaming weather data."
  type        = string
  default     = "streaming_weather"
}