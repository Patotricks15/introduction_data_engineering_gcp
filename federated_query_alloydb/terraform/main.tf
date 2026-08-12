data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_service" "services" {
  for_each = toset([
    "alloydb.googleapis.com",
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_compute_network" "alloydb" {
  name                    = "alloydb-federation-network"
  auto_create_subnetworks = false

  depends_on = [google_project_service.services]
}

resource "google_compute_global_address" "private_services" {
  name          = "alloydb-federation-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.alloydb.id
}

resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.alloydb.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]

  depends_on = [google_project_service.services]
}

resource "random_password" "database" {
  length  = 24
  special = false
}

resource "google_alloydb_cluster" "demo" {
  cluster_id       = "federated-query-cluster"
  location         = var.region
  database_version = "POSTGRES_15"

  network_config {
    network            = google_compute_network.alloydb.id
    allocated_ip_range = google_compute_global_address.private_services.name
  }

  initial_user {
    user     = "federated_user"
    password = random_password.database.result
  }

  continuous_backup_config {
    enabled = false
  }

  automated_backup_policy {
    enabled = false
  }

  deletion_protection = false
  deletion_policy     = "FORCE"

  depends_on = [google_service_networking_connection.private_services]
}

resource "google_alloydb_instance" "primary" {
  cluster       = google_alloydb_cluster.demo.name
  instance_id   = "federated-query-primary"
  instance_type = "PRIMARY"

  availability_type = "ZONAL"

  machine_config {
    cpu_count = 2
  }

  network_config {
    enable_public_ip = true

    authorized_external_networks {
      cidr_range = var.operator_cidr
    }
  }

  depends_on = [google_service_networking_connection.private_services]
}

resource "google_bigquery_dataset" "analytics" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Federated AlloyDB Analytics"
  description                = "Native reference data joined with live AlloyDB data."
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table" "region_targets" {
  dataset_id          = google_bigquery_dataset.analytics.dataset_id
  table_id            = "region_targets"
  description         = "Native BigQuery targets joined with AlloyDB order data."
  deletion_protection = false
  schema = jsonencode([
    { name = "region_code", type = "STRING", mode = "REQUIRED" },
    { name = "region_name", type = "STRING", mode = "REQUIRED" },
    { name = "revenue_target", type = "NUMERIC", mode = "REQUIRED" },
  ])
}

resource "google_bigquery_connection" "alloydb" {
  connection_id = "alloydb-federation"
  location      = var.region
  friendly_name = "AlloyDB federated connection"
  description   = "BigQuery Connector Framework connection to the demo AlloyDB instance."

  configuration {
    connector_id = "google-alloydb"

    asset {
      database              = "postgres"
      google_cloud_resource = "//alloydb.googleapis.com/${google_alloydb_instance.primary.id}"
    }

    authentication {
      username_password {
        username = "federated_user"

        password {
          plaintext = random_password.database.result
        }
      }
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "connection_alloydb_client" {
  project = var.project_id
  role    = "roles/alloydb.client"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-bigqueryconnection.iam.gserviceaccount.com"

  depends_on = [google_bigquery_connection.alloydb]
}