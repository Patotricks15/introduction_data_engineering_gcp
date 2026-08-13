variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Regional location for Dataplex and BigQuery resources."
  type        = string
  default     = "us-central1"
}

variable "runner_member" {
  description = "IAM member that can impersonate the data quality service account."
  type        = string
}

variable "sales_steward_member" {
  description = "Optional IAM member allowed to curate the sales domain."
  type        = string
  default     = ""
}

variable "customer_analyst_member" {
  description = "Optional IAM member allowed to read the customer domain."
  type        = string
  default     = ""
}