variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "region" {
  description = "Region used by Dataproc Serverless and Cloud Storage."
  type        = string
  default     = "us-central1"
}

variable "dataset_id" {
  description = "BigQuery dataset that receives the Spark output."
  type        = string
  default     = "serverless_spark_demo"
}

variable "runner_member" {
  description = "IAM member allowed to submit batches as the Spark service account."
  type        = string
}