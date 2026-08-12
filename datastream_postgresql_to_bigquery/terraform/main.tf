provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "datastream.googleapis.com",
    "sqladmin.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

data "google_datastream_static_ips" "datastream" {
  location = var.region

  depends_on = [google_project_service.services]
}

resource "random_password" "postgres" {
  length  = 24
  special = false
}

resource "random_password" "datastream" {
  length  = 24
  special = false
}

resource "google_sql_database_instance" "source" {
  name                = "datastream-postgres-source"
  database_version    = "POSTGRES_15"
  region              = var.region
  deletion_protection = false

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
    disk_size         = 10
    disk_type         = "PD_HDD"

    database_flags {
      name  = "cloudsql.logical_decoding"
      value = "on"
    }

    ip_configuration {
      ipv4_enabled = true

      authorized_networks {
        name  = "lab-runner"
        value = var.operator_cidr
      }

      dynamic "authorized_networks" {
        for_each = {
          for index, ip in data.google_datastream_static_ips.datastream.static_ips : index => ip
        }

        content {
          name  = "datastream-${authorized_networks.key}"
          value = authorized_networks.value
        }
      }
    }
  }

  depends_on = [google_project_service.services]
}

resource "google_sql_database" "source" {
  name     = "commerce"
  instance = google_sql_database_instance.source.name
}

resource "google_sql_user" "postgres" {
  name     = "postgres"
  instance = google_sql_database_instance.source.name
  password = random_password.postgres.result
}

resource "google_sql_user" "datastream" {
  name     = "datastream_user"
  instance = google_sql_database_instance.source.name
  password = random_password.datastream.result
}

resource "google_bigquery_dataset" "replica" {
  dataset_id                 = "postgres_replica"
  friendly_name              = "PostgreSQL Datastream replica"
  description                = "Temporary BigQuery destination for the Datastream CDC lab."
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "datastream_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-datastream.iam.gserviceaccount.com"

  depends_on = [google_project_service.services]
}

resource "google_datastream_connection_profile" "source" {
  count = var.create_stream ? 1 : 0

  display_name          = "PostgreSQL source"
  location              = var.region
  connection_profile_id = "postgresql-source"

  postgresql_profile {
    hostname = google_sql_database_instance.source.public_ip_address
    port     = 5432
    username = google_sql_user.datastream.name
    password = google_sql_user.datastream.password
    database = google_sql_database.source.name
  }

  depends_on = [google_project_service.services]
}

resource "google_datastream_connection_profile" "destination" {
  count = var.create_stream ? 1 : 0

  display_name          = "BigQuery destination"
  location              = var.region
  connection_profile_id = "bigquery-destination"

  bigquery_profile {}

  depends_on = [google_project_service.services]
}

resource "google_datastream_stream" "replication" {
  count = var.create_stream ? 1 : 0

  display_name  = "PostgreSQL replication to BigQuery"
  location      = var.region
  stream_id     = "postgresql-to-bigquery"
  desired_state = "RUNNING"

  source_config {
    source_connection_profile = google_datastream_connection_profile.source[0].id

    postgresql_source_config {
      publication      = "datastream_publication"
      replication_slot = "datastream_slot"

      include_objects {
        postgresql_schemas {
          schema = "public"

          postgresql_tables {
            table = "orders"
          }
        }
      }
    }
  }

  destination_config {
    destination_connection_profile = google_datastream_connection_profile.destination[0].id

    bigquery_destination_config {
      data_freshness = "0s"

      single_target_dataset {
        dataset_id = google_bigquery_dataset.replica.id
      }
    }
  }

  backfill_all {}

  depends_on = [google_project_iam_member.datastream_bigquery]
}
