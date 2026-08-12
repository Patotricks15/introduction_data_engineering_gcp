variable "project_id" {
  description = "GCP project where the lab resources are created."
  type        = string

  validation {
    condition     = length(var.project_id) > 0
    error_message = "project_id must not be empty."
  }
}

variable "region" {
  description = "GCP region for Cloud SQL, Datastream, and BigQuery."
  type        = string
  default     = "us-central1"
}

variable "operator_cidr" {
  description = "Public CIDR allowed to initialize the PostgreSQL database."
  type        = string
  default     = "127.0.0.1/32"

  validation {
    condition     = can(cidrhost(var.operator_cidr, 0))
    error_message = "operator_cidr must be a valid IPv4 or IPv6 CIDR."
  }
}

variable "create_stream" {
  description = "Create and start Datastream after PostgreSQL is initialized."
  type        = bool
  default     = false
}
