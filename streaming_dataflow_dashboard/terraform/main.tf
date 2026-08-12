locals {
  dataflow_bucket_name = "${var.project_id}-streaming-dataflow"
  event_schema = [
    { name = "observed_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "published_at", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "city", type = "STRING", mode = "REQUIRED" },
    { name = "country", type = "STRING", mode = "REQUIRED" },
    { name = "latitude", type = "FLOAT", mode = "REQUIRED" },
    { name = "longitude", type = "FLOAT", mode = "REQUIRED" },
    { name = "temperature_c", type = "FLOAT", mode = "REQUIRED" },
    { name = "relative_humidity", type = "INTEGER", mode = "REQUIRED" },
    { name = "wind_speed_kmh", type = "FLOAT", mode = "REQUIRED" },
    { name = "weather_code", type = "INTEGER", mode = "REQUIRED" },
  ]
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "compute.googleapis.com",
    "dataflow.googleapis.com",
    "iam.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_pubsub_topic" "weather" {
  name = "weather-observations"

  depends_on = [google_project_service.services]
}

resource "google_storage_bucket" "dataflow" {
  name                        = local.dataflow_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_dataset" "streaming" {
  dataset_id                 = var.dataset_id
  friendly_name              = "Streaming Weather Dashboard"
  description                = "Real-time weather observations delivered by Dataflow."
  location                   = var.location
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table" "weather_events" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "weather_events"
  description         = "Raw weather events streamed from Pub/Sub by Dataflow."
  deletion_protection = false
  schema              = jsonencode(local.event_schema)

  time_partitioning {
    type  = "DAY"
    field = "observed_at"
  }

  clustering = ["city"]
}

resource "google_bigquery_table" "latest_weather" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "latest_weather"
  description         = "Latest observation per city for dashboard scorecards and maps."
  deletion_protection = false

  view {
    use_legacy_sql = false
    query          = <<-SQL
      SELECT
        observed_at,
        city,
        country,
        latitude,
        longitude,
        temperature_c,
        relative_humidity,
        wind_speed_kmh,
        weather_code
      FROM `${var.project_id}.${google_bigquery_dataset.streaming.dataset_id}.${google_bigquery_table.weather_events.table_id}`
      QUALIFY ROW_NUMBER() OVER (PARTITION BY city ORDER BY observed_at DESC, published_at DESC) = 1
    SQL
  }
}

resource "google_bigquery_table" "weather_trends" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "weather_trends"
  description         = "Time-series metrics for the real-time dashboard."
  deletion_protection = false

  view {
    use_legacy_sql = false
    query          = <<-SQL
      SELECT
        TIMESTAMP_TRUNC(observed_at, MINUTE) AS observation_minute,
        city,
        ANY_VALUE(country) AS country,
        AVG(temperature_c) AS avg_temperature_c,
        AVG(relative_humidity) AS avg_relative_humidity,
        AVG(wind_speed_kmh) AS avg_wind_speed_kmh
      FROM `${var.project_id}.${google_bigquery_dataset.streaming.dataset_id}.${google_bigquery_table.weather_events.table_id}`
      WHERE observed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
      GROUP BY observation_minute, city
    SQL
  }
}

resource "google_service_account" "dataflow_worker" {
  account_id   = "streaming-dataflow-worker"
  display_name = "Streaming Dataflow worker"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "dataflow_worker_roles" {
  for_each = toset([
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/dataflow.worker",
    "roles/pubsub.subscriber",
    "roles/storage.objectAdmin",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dataflow_worker.email}"
}