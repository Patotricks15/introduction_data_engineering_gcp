locals {
  bucket_name = "${var.project_id}-esports-streaming"
  event_schema = [
    { name = "event_id", type = "STRING", mode = "REQUIRED" },
    { name = "event_time", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "match_id", type = "STRING", mode = "REQUIRED" },
    { name = "player_id", type = "STRING", mode = "REQUIRED" },
    { name = "event_type", type = "STRING", mode = "REQUIRED" },
    { name = "action", type = "STRING", mode = "REQUIRED" },
    { name = "score_delta", type = "INTEGER", mode = "REQUIRED" },
    { name = "message", type = "STRING", mode = "NULLABLE" },
    { name = "display_name", type = "STRING", mode = "REQUIRED" },
    { name = "team", type = "STRING", mode = "REQUIRED" },
    { name = "region", type = "STRING", mode = "REQUIRED" },
    { name = "rank", type = "STRING", mode = "REQUIRED" },
    { name = "processed_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ]
  error_schema = [
    { name = "payload", type = "STRING", mode = "REQUIRED" },
    { name = "error", type = "STRING", mode = "REQUIRED" },
    { name = "failed_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ]
}

resource "google_project_service" "services" {
  for_each = toset([
    "bigquery.googleapis.com",
    "bigtable.googleapis.com",
    "bigtableadmin.googleapis.com",
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

resource "google_pubsub_topic" "events" {
  name = "esports-events"

  depends_on = [google_project_service.services]
}

resource "google_storage_bucket" "dataflow" {
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  depends_on = [google_project_service.services]
}

resource "google_bigtable_instance" "profiles" {
  name                = "esports-profiles"
  display_name        = "E-sports player profiles"
  deletion_protection = false

  cluster {
    cluster_id   = "esports-profiles-c1"
    zone         = var.zone
    num_nodes    = 1
    storage_type = "SSD"
  }

  depends_on = [google_project_service.services]
}

resource "google_bigtable_table" "players" {
  name          = "players"
  instance_name = google_bigtable_instance.profiles.name

  column_family {
    family = "profile"
  }
}

resource "google_bigtable_gc_policy" "profile_versions" {
  instance_name = google_bigtable_instance.profiles.name
  table         = google_bigtable_table.players.name
  column_family = "profile"

  max_version {
    number = 1
  }

  depends_on = [google_bigtable_table.players]
}

resource "google_bigquery_dataset" "streaming" {
  dataset_id                 = var.dataset_id
  friendly_name              = "E-sports Streaming Analytics"
  description                = "Enriched gameplay and chat events produced by Apache Beam."
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [google_project_service.services]
}

resource "google_bigquery_table" "events" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "enriched_events"
  description         = "Gameplay and chat events enriched with Bigtable player profiles."
  deletion_protection = false
  schema              = jsonencode(local.event_schema)

  time_partitioning {
    type  = "DAY"
    field = "event_time"
  }

  clustering = ["event_type", "team"]
}

resource "google_bigquery_table" "errors" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "dead_letter_events"
  description         = "Malformed Pub/Sub messages rejected by the Beam parser."
  deletion_protection = false
  schema              = jsonencode(local.error_schema)
}

resource "google_bigquery_table" "leaderboard" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "live_leaderboard"
  description         = "Dashboard-ready player scores from the last hour."
  deletion_protection = false

  view {
    use_legacy_sql = false
    query          = <<-SQL
      SELECT
        player_id,
        ANY_VALUE(display_name) AS display_name,
        ANY_VALUE(team) AS team,
        ANY_VALUE(region) AS region,
        ANY_VALUE(rank) AS rank,
        SUM(score_delta) AS score,
        COUNTIF(action = 'kill') AS kills,
        COUNTIF(action = 'assist') AS assists,
        MAX(event_time) AS last_event
      FROM `${var.project_id}.${google_bigquery_dataset.streaming.dataset_id}.${google_bigquery_table.events.table_id}`
      WHERE event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
      GROUP BY player_id
    SQL
  }
}

resource "google_bigquery_table" "chat" {
  dataset_id          = google_bigquery_dataset.streaming.dataset_id
  table_id            = "live_chat"
  description         = "Recent enriched chat messages for Streamlit monitoring."
  deletion_protection = false

  view {
    use_legacy_sql = false
    query          = <<-SQL
      SELECT event_time, match_id, display_name, team, region, message
      FROM `${var.project_id}.${google_bigquery_dataset.streaming.dataset_id}.${google_bigquery_table.events.table_id}`
      WHERE event_type = 'chat'
        AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
    SQL
  }
}

resource "google_service_account" "dataflow" {
  account_id   = "esports-dataflow-worker"
  display_name = "E-sports Beam pipeline worker"

  depends_on = [google_project_service.services]
}

resource "google_project_iam_member" "dataflow_roles" {
  for_each = toset([
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/bigtable.reader",
    "roles/dataflow.worker",
    "roles/pubsub.subscriber",
    "roles/storage.objectAdmin",
  ])

  project = var.project_id
  role    = each.value
  member  = google_service_account.dataflow.member
}

resource "google_service_account_iam_member" "runner_can_act_as" {
  service_account_id = google_service_account.dataflow.name
  role               = "roles/iam.serviceAccountUser"
  member             = var.runner_member
}