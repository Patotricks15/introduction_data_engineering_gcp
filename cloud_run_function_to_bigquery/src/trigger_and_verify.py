from __future__ import annotations

import argparse
import time
import urllib.request
from pathlib import Path

from google.cloud import bigquery, storage


DATA_URL = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv"
EXPECTED_ROW_COUNT = 244


def download_data(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DATA_URL, timeout=60) as response:
        destination.write_bytes(response.read())


def upload_data(project_id: str, bucket_name: str, source: Path) -> None:
    client = storage.Client(project=project_id)
    client.bucket(bucket_name).blob(source.name).upload_from_filename(source)


def wait_for_rows(
    project_id: str,
    dataset_id: str,
    table_id: str,
    expected_rows: int = EXPECTED_ROW_COUNT,
    attempts: int = 40,
    poll_seconds: float = 5,
) -> int:
    client = bigquery.Client(project=project_id)
    table_name = f"{project_id}.{dataset_id}.{table_id}"
    for _ in range(attempts):
        row_count = client.get_table(table_name).num_rows
        if row_count == expected_rows:
            return row_count
        time.sleep(poll_seconds)
    raise TimeoutError(
        f"Expected {expected_rows} rows in {table_name} after {attempts} attempts"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger and verify the CSV loader.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--csv-path", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    download_data(args.csv_path)
    upload_data(args.project_id, args.bucket_name, args.csv_path)
    row_count = wait_for_rows(args.project_id, args.dataset_id, args.table_id)
    print(f"Function load verified: {row_count} rows in BigQuery.")


if __name__ == "__main__":
    main()