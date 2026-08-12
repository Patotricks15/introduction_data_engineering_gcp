from __future__ import annotations

import os
from typing import Any, Mapping

import functions_framework
from google.cloud import bigquery


def load_object(
    event_data: Mapping[str, Any],
    dataset_id: str,
    table_id: str,
    client: bigquery.Client,
) -> int:
    """Load one finalized CSV object into the configured BigQuery table."""
    bucket = str(event_data["bucket"])
    object_name = str(event_data["name"])
    if not object_name.lower().endswith(".csv"):
        print(f"Skipping non-CSV object: gs://{bucket}/{object_name}")
        return 0

    destination = f"{client.project}.{dataset_id}.{table_id}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    load_job = client.load_table_from_uri(
        f"gs://{bucket}/{object_name}", destination, job_config=job_config
    )
    load_job.result()
    row_count = client.get_table(destination).num_rows
    print(f"Loaded {row_count} rows from {object_name} into {destination}.")
    return row_count


@functions_framework.cloud_event
def load_csv_to_bigquery(cloud_event: Any) -> None:
    dataset_id = os.environ["BIGQUERY_DATASET"]
    table_id = os.environ["BIGQUERY_TABLE"]
    load_object(cloud_event.data, dataset_id, table_id, bigquery.Client())