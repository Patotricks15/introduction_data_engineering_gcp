variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for Dataflow and Cloud Storage."
  type        = string
  default     = "us-central1"
}

variable "runner_member" {
  description = "Authenticated identity allowed to submit Dataflow jobs as the worker account."
  type        = string
}