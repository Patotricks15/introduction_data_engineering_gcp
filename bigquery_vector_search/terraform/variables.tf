variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Google Cloud region used by the provider."
  type        = string
  default     = "us-central1"
}

variable "location" {
  description = "BigQuery dataset and connection location."
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset containing documents, model, and embeddings."
  type        = string
  default     = "vector_search_demo"
}

variable "connection_id" {
  description = "BigQuery connection used to call Vertex AI."
  type        = string
  default     = "vertex-ai-connection"
}