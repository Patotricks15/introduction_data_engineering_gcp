from __future__ import annotations

import argparse
import csv
import urllib.request
from pathlib import Path


DATA_URL = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv"
EXPECTED_COLUMNS = [
    "total_bill",
    "tip",
    "sex",
    "smoker",
    "day",
    "time",
    "size",
]


def download_tips(destination: Path, source_url: str = DATA_URL) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(source_url, timeout=30) as response:
        destination.write_bytes(response.read())

    with destination.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames != EXPECTED_COLUMNS:
            raise ValueError(f"Unexpected tips schema: {reader.fieldnames}")
        row_count = sum(1 for _ in reader)

    if row_count == 0:
        raise ValueError("The downloaded tips dataset is empty.")
    return row_count


def upload_file(project_id: str, bucket_name: str, source: Path) -> str:
    from google.cloud import storage

    client = storage.Client(project=project_id)
    blob = client.bucket(bucket_name).blob(f"input/{source.name}")
    blob.upload_from_filename(source)
    return f"gs://{bucket_name}/{blob.name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare public data for Spark.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    row_count = download_tips(args.output)
    uri = upload_file(args.project_id, args.bucket_name, args.output)
    print(f"Uploaded {row_count} rows to {uri}")


if __name__ == "__main__":
    main()