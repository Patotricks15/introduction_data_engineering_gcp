locals {
  raw_bucket_name       = "${var.project_id}-mesh-raw"
  governance_aspect_key = "${data.google_project.current.number}.${var.region}.domain-governance"
  domain_aspect_template = jsonencode({
    type = "record"
    recordFields = [
      {
        name        = "domain"
        type        = "string"
        index       = 1
        annotations = { displayName = "Business domain" }
      },
      {
        name        = "owner"
        type        = "string"
        index       = 2
        annotations = { displayName = "Data owner" }
      },
      {
        name  = "classification"
        type  = "enum"
        index = 3
        enumValues = [
          { name = "PUBLIC", index = 1 },
          { name = "INTERNAL", index = 2 },
          { name = "CONFIDENTIAL", index = 3 },
        ]
        annotations = { displayName = "Classification" }
      },
      {
        name        = "quality_slo"
        type        = "double"
        index       = 4
        annotations = { displayName = "Quality SLO" }
      },
    ]
  })
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "datacatalog.googleapis.com",
    "dataplex.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "raw" {
  name                        = local.raw_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  labels = {
    domain = "shared"
    layer  = "raw"
  }

  depends_on = [google_project_service.services]
}

resource "google_bigquery_dataset" "domains" {
  for_each = {
    sales     = "Sales domain serving orders and revenue metrics."
    customers = "Customer domain serving governed customer profiles."
  }

  dataset_id                 = "mesh_${each.key}"
  friendly_name              = "${title(each.key)} Data Product"
  description                = each.value
  location                   = var.region
  delete_contents_on_destroy = true

  labels = {
    domain = each.key
    mesh   = "knowledge-catalog"
  }

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table" "orders" {
  dataset_id          = google_bigquery_dataset.domains["sales"].dataset_id
  table_id            = "orders"
  description         = "Curated sales orders governed as a sales data product."
  deletion_protection = false
  schema = jsonencode([
    { name = "order_id", type = "STRING", mode = "REQUIRED" },
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "order_date", type = "DATE", mode = "REQUIRED" },
    { name = "status", type = "STRING", mode = "REQUIRED" },
    { name = "amount", type = "NUMERIC", mode = "REQUIRED" },
  ])

  time_partitioning {
    type  = "DAY"
    field = "order_date"
  }

  clustering = ["status", "customer_id"]
}

resource "google_bigquery_table" "customers" {
  dataset_id          = google_bigquery_dataset.domains["customers"].dataset_id
  table_id            = "customer_profiles"
  description         = "Governed customer profiles with restricted domain access."
  deletion_protection = false
  schema = jsonencode([
    { name = "customer_id", type = "STRING", mode = "REQUIRED" },
    { name = "full_name", type = "STRING", mode = "REQUIRED" },
    { name = "email", type = "STRING", mode = "REQUIRED" },
    { name = "country", type = "STRING", mode = "REQUIRED" },
    { name = "consent", type = "BOOLEAN", mode = "REQUIRED" },
  ])

  clustering = ["country", "consent"]
}

resource "google_service_account" "quality" {
  account_id   = "mesh-quality-runner"
  display_name = "Dataplex data quality runner"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "quality_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = google_service_account.quality.member
}

resource "google_bigquery_dataset_iam_member" "quality_data_editor" {
  for_each = google_bigquery_dataset.domains

  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.quality.member
}

resource "google_service_account_iam_member" "runner_can_act_as" {
  service_account_id = google_service_account.quality.name
  role               = "roles/iam.serviceAccountUser"
  member             = var.runner_member
}

resource "google_service_account_iam_member" "dataplex_can_run_as_quality" {
  service_account_id = google_service_account.quality.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-dataplex.iam.gserviceaccount.com"
}

resource "google_bigquery_dataset_iam_member" "sales_steward" {
  count = var.sales_steward_member == "" ? 0 : 1

  dataset_id = google_bigquery_dataset.domains["sales"].dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = var.sales_steward_member
}

resource "google_bigquery_dataset_iam_member" "customer_analyst" {
  count = var.customer_analyst_member == "" ? 0 : 1

  dataset_id = google_bigquery_dataset.domains["customers"].dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = var.customer_analyst_member
}

resource "google_dataplex_lake" "mesh" {
  name         = "enterprise-data-mesh"
  location     = var.region
  display_name = "Enterprise Data Mesh"
  description  = "Governed lake organizing shared raw data and curated domain products."

  labels = { architecture = "data-mesh" }

  depends_on = [google_project_service.services]
}

resource "google_dataplex_zone" "raw" {
  name         = "shared-raw"
  location     = var.region
  lake         = google_dataplex_lake.mesh.name
  type         = "RAW"
  display_name = "Shared Raw Zone"

  discovery_spec {
    enabled  = true
    schedule = "0 * * * *"
    json_options { encoding = "UTF-8" }
  }

  resource_spec { location_type = "SINGLE_REGION" }
}

resource "google_dataplex_zone" "curated" {
  name         = "domain-curated"
  location     = var.region
  lake         = google_dataplex_lake.mesh.name
  type         = "CURATED"
  display_name = "Domain Curated Zone"

  discovery_spec { enabled = true }
  resource_spec { location_type = "SINGLE_REGION" }
}

resource "google_dataplex_asset" "raw_bucket" {
  name          = "raw-object-store"
  location      = var.region
  lake          = google_dataplex_lake.mesh.name
  dataplex_zone = google_dataplex_zone.raw.name
  display_name  = "Raw Object Store"

  discovery_spec { enabled = true }
  resource_spec {
    name             = "projects/${var.project_id}/buckets/${google_storage_bucket.raw.name}"
    type             = "STORAGE_BUCKET"
    read_access_mode = "DIRECT"
  }
}

resource "google_dataplex_asset" "domain_datasets" {
  for_each = google_bigquery_dataset.domains

  name          = "${each.key}-domain"
  location      = var.region
  lake          = google_dataplex_lake.mesh.name
  dataplex_zone = google_dataplex_zone.curated.name
  display_name  = "${title(each.key)} Domain Dataset"

  discovery_spec { enabled = true }
  resource_spec {
    name             = "projects/${var.project_id}/datasets/${each.value.dataset_id}"
    type             = "BIGQUERY_DATASET"
    read_access_mode = "DIRECT"
  }
}

resource "google_dataplex_aspect_type" "domain_governance" {
  project           = data.google_project.current.number
  aspect_type_id    = "domain-governance"
  location          = var.region
  display_name      = "Domain Governance"
  description       = "Ownership, classification, and quality SLO for mesh assets."
  metadata_template = local.domain_aspect_template

  depends_on = [google_project_service.services]
}

resource "google_dataplex_entry_group" "products" {
  for_each = toset(["sales", "customers"])

  project        = data.google_project.current.number
  entry_group_id = "${each.key}-products"
  location       = var.region
  display_name   = "${title(each.key)} Data Products"
  description    = "Discoverable entries secured for the ${each.key} domain."

  depends_on = [google_project_service.services]
}

resource "google_dataplex_entry_group_iam_member" "sales_steward" {
  count = var.sales_steward_member == "" ? 0 : 1

  project        = data.google_project.current.number
  location       = var.region
  entry_group_id = google_dataplex_entry_group.products["sales"].entry_group_id
  role           = "roles/dataplex.catalogEditor"
  member         = var.sales_steward_member
}

resource "google_dataplex_entry_group_iam_member" "customer_analyst" {
  count = var.customer_analyst_member == "" ? 0 : 1

  project        = data.google_project.current.number
  location       = var.region
  entry_group_id = google_dataplex_entry_group.products["customers"].entry_group_id
  role           = "roles/dataplex.catalogViewer"
  member         = var.customer_analyst_member
}

resource "google_dataplex_entry_type" "data_product" {
  project       = data.google_project.current.number
  entry_type_id = "mesh-data-product"
  location      = var.region
  display_name  = "Mesh Data Product"
  description   = "A discoverable domain-owned analytical data product."
  platform      = "BigQuery"
  system        = "DATA_MESH"

  required_aspects {
    type = google_dataplex_aspect_type.domain_governance.name
  }
}

resource "google_dataplex_entry" "domain_products" {
  for_each = {
    sales = {
      resource       = "bigquery:${var.project_id}.${google_bigquery_dataset.domains["sales"].dataset_id}.${google_bigquery_table.orders.table_id}"
      classification = "INTERNAL"
      owner          = "sales-domain@example.com"
    }
    customers = {
      resource       = "bigquery:${var.project_id}.${google_bigquery_dataset.domains["customers"].dataset_id}.${google_bigquery_table.customers.table_id}"
      classification = "CONFIDENTIAL"
      owner          = "customer-domain@example.com"
    }
  }

  entry_id             = "${each.key}-product"
  entry_group_id       = google_dataplex_entry_group.products[each.key].entry_group_id
  entry_type           = google_dataplex_entry_type.data_product.name
  location             = var.region
  project              = data.google_project.current.number
  fully_qualified_name = each.value.resource

  entry_source {
    display_name = "${title(each.key)} Data Product"
    description  = "Governed ${each.key} domain product published through Dataplex Universal Catalog."
    platform     = "BigQuery"
    system       = "DATA_MESH"
    resource     = each.value.resource
    labels       = { domain = each.key }
  }

  aspects {
    aspect_key = local.governance_aspect_key
    aspect {
      data = jsonencode({
        domain         = each.key
        owner          = each.value.owner
        classification = each.value.classification
        quality_slo    = 0.95
      })
    }
  }
}

resource "google_dataplex_data_product" "domains" {
  for_each = {
    sales     = "sales-domain@example.com"
    customers = "customer-domain@example.com"
  }

  data_product_id = "${each.key}-analytics"
  location        = var.region
  display_name    = "${title(each.key)} Analytics"
  description     = "Governed ${each.key} data product for cross-domain analytics."
  owner_emails    = [each.value]

  labels = { domain = each.key }

  depends_on = [google_project_service.services]
}

resource "google_dataplex_data_product_data_asset" "domain_tables" {
  for_each = {
    sales = {
      product  = google_dataplex_data_product.domains["sales"].data_product_id
      resource = "//bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.domains["sales"].dataset_id}"
    }
    customers = {
      product  = google_dataplex_data_product.domains["customers"].data_product_id
      resource = "//bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.domains["customers"].dataset_id}"
    }
  }

  data_asset_id   = "${each.key}-table"
  data_product_id = each.value.product
  location        = var.region
  resource        = each.value.resource
}

resource "google_dataplex_datascan" "orders_quality" {
  data_scan_id = "orders-quality"
  location     = var.region
  display_name = "Orders Data Quality"
  description  = "Checks completeness, validity, uniqueness, and positive order values."

  data {
    resource = "//bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.domains["sales"].dataset_id}/tables/${google_bigquery_table.orders.table_id}"
  }

  execution_spec {
    trigger {
      on_demand {}
    }
  }

  execution_identity {
    service_account { email = google_service_account.quality.email }
  }

  data_quality_spec {
    catalog_publishing_enabled = true

    rules {
      name      = "order_id_complete"
      dimension = "COMPLETENESS"
      column    = "order_id"
      threshold = 1.0
      non_null_expectation {}
    }
    rules {
      name      = "order_id_unique"
      dimension = "UNIQUENESS"
      column    = "order_id"
      threshold = 1.0
      uniqueness_expectation {}
    }
    rules {
      name      = "valid_status"
      dimension = "VALIDITY"
      column    = "status"
      threshold = 1.0
      set_expectation { values = ["PAID", "SHIPPED", "CANCELLED"] }
    }
    rules {
      name      = "positive_amount"
      dimension = "VALIDITY"
      column    = "amount"
      threshold = 1.0
      range_expectation {
        min_value          = "0"
        strict_min_enabled = true
      }
    }
  }

  depends_on = [google_service_account_iam_member.dataplex_can_run_as_quality]
}

resource "google_dataplex_datascan" "customers_quality" {
  data_scan_id = "customers-quality"
  location     = var.region
  display_name = "Customers Data Quality"
  description  = "Checks customer identifiers, emails, and consent values."

  data {
    resource = "//bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.domains["customers"].dataset_id}/tables/${google_bigquery_table.customers.table_id}"
  }

  execution_spec {
    trigger {
      on_demand {}
    }
  }

  execution_identity {
    service_account { email = google_service_account.quality.email }
  }

  data_quality_spec {
    catalog_publishing_enabled = true

    rules {
      name      = "customer_id_complete"
      dimension = "COMPLETENESS"
      column    = "customer_id"
      threshold = 1.0
      non_null_expectation {}
    }
    rules {
      name      = "customer_id_unique"
      dimension = "UNIQUENESS"
      column    = "customer_id"
      threshold = 1.0
      uniqueness_expectation {}
    }
    rules {
      name      = "valid_email"
      dimension = "VALIDITY"
      column    = "email"
      threshold = 1.0
      regex_expectation { regex = "^[^@]+@[^@]+[.][^@]+$" }
    }
    rules {
      name      = "consent_complete"
      dimension = "COMPLETENESS"
      column    = "consent"
      threshold = 1.0
      non_null_expectation {}
    }
  }


  depends_on = [google_service_account_iam_member.dataplex_can_run_as_quality]
}