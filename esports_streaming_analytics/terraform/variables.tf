variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for Dataflow, Bigtable, and Cloud Storage."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zone for the single-node demo Bigtable cluster."
  type        = string
  default     = "us-central1-a"
}

variable "dataset_id" {
  description = "BigQuery dataset for enriched e-sports events."
  type        = string
  default     = "esports_streaming"
}

variable "runner_member" {
  description = "Authenticated identity allowed to launch Dataflow with the worker service account."
  type        = string
}