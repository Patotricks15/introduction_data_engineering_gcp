variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region for AlloyDB, BigQuery, and the connection."
  type        = string
  default     = "us-central1"
}

variable "operator_cidr" {
  description = "Public CIDR allowed to initialize the demo database."
  type        = string
}

variable "dataset_id" {
  description = "BigQuery dataset containing native reference data."
  type        = string
  default     = "federated_analytics"
}