locals {
  bucket_name = "${var.project_id}-lakehouse-qwik-start"
  customer_schema = [
    { name = "customer_id", type = "INTEGER", mode = "REQUIRED" },
    { name = "first_name", type = "STRING", mode = "REQUIRED" },
    { name = "last_name", type = "STRING", mode = "REQUIRED" },
    { name = "company", type = "STRING", mode = "NULLABLE" },
    {
      name       = "address"
      type       = "STRING"
      mode       = "NULLABLE"
      policyTags = { names = [google_data_catalog_policy_tag.sensitive.name] }
    },
    { name = "city", type = "STRING", mode = "NULLABLE" },
    { name = "state", type = "STRING", mode = "NULLABLE" },
    { name = "country", type = "STRING", mode = "NULLABLE" },
    {
      name       = "postal_code"
      type       = "STRING"
      mode       = "NULLABLE"
      policyTags = { names = [google_data_catalog_policy_tag.sensitive.name] }
    },
    {
      name       = "phone"
      type       = "STRING"
      mode       = "NULLABLE"
      policyTags = { names = [google_data_catalog_policy_tag.sensitive.name] }
    },
    { name = "fax", type = "STRING", mode = "NULLABLE" },
    { name = "email", type = "STRING", mode = "REQUIRED" },
    { name = "support_rep_id", type = "INTEGER", mode = "NULLABLE" }
  ]
  invoice_schema = [
    { name = "invoice_id", type = "INTEGER", mode = "REQUIRED" },
    { name = "customer_id", type = "INTEGER", mode = "REQUIRED" },
    { name = "invoice_date", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "billing_address", type = "STRING", mode = "NULLABLE" },
    { name = "billing_city", type = "STRING", mode = "NULLABLE" },
    { name = "billing_state", type = "STRING", mode = "NULLABLE" },
    { name = "billing_country", type = "STRING", mode = "NULLABLE" },
    { name = "billing_postal_code", type = "STRING", mode = "NULLABLE" },
    { name = "total", type = "NUMERIC", mode = "REQUIRED" }
  ]
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "datacatalog.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "data_lake" {
  name                        = local.bucket_name
  location                    = var.location
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_dataset" "demo" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Lakehouse Qwik Start"
  description                = "BigLake external tables backed by the Cloud Storage data lake."
  location                   = var.location
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_connection" "lakehouse" {
  connection_id = "lakehouse-connection"
  location      = var.location
  friendly_name = "Lakehouse Cloud Resource connection"
  description   = "Delegates BigQuery access to objects in the data lake."

  cloud_resource {}

  depends_on = [google_project_service.services]
}

resource "google_storage_bucket_iam_member" "connection_reader" {
  bucket = google_storage_bucket.data_lake.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_bigquery_connection.lakehouse.cloud_resource[0].service_account_id}"
}

resource "google_data_catalog_taxonomy" "lakehouse" {
  region                 = lower(var.location)
  display_name           = "Lakehouse data classification"
  description            = "Column-level security taxonomy for the Lakehouse demo."
  activated_policy_types = ["FINE_GRAINED_ACCESS_CONTROL"]

  depends_on = [google_project_service.services]
}

resource "google_data_catalog_policy_tag" "sensitive" {
  taxonomy     = google_data_catalog_taxonomy.lakehouse.id
  display_name = "Sensitive customer data"
  description  = "Address, postal code, and phone fields requiring explicit access."
}

resource "google_bigquery_table" "customers" {
  count = var.create_tables ? 1 : 0

  dataset_id          = google_bigquery_dataset.demo.dataset_id
  table_id            = "customers_biglake"
  description         = "Governed BigLake table over customer CSV data in Cloud Storage."
  deletion_protection = false
  schema              = jsonencode(local.customer_schema)

  external_data_configuration {
    autodetect    = false
    connection_id = google_bigquery_connection.lakehouse.name
    source_format = "CSV"
    source_uris   = ["gs://${google_storage_bucket.data_lake.name}/customer.csv"]

    csv_options {
      skip_leading_rows = 1
      quote             = "\""
    }
  }

  depends_on = [google_storage_bucket_iam_member.connection_reader]
}

resource "google_bigquery_table" "invoices" {
  count = var.create_tables ? 1 : 0

  dataset_id          = google_bigquery_dataset.demo.dataset_id
  table_id            = "invoices_biglake"
  description         = "External invoice table upgraded with a Cloud Resource connection."
  deletion_protection = false
  schema              = jsonencode(local.invoice_schema)

  external_data_configuration {
    autodetect    = false
    connection_id = google_bigquery_connection.lakehouse.name
    source_format = "CSV"
    source_uris   = ["gs://${google_storage_bucket.data_lake.name}/invoice.csv"]

    csv_options {
      skip_leading_rows = 1
      quote             = "\""
    }
  }

  depends_on = [google_storage_bucket_iam_member.connection_reader]
}