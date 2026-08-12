import argparse
import json
from typing import Any


def load_jsonl_prefix(project_id: str, bucket_name: str, prefix: str) -> list[dict[str, Any]]:
    from google.cloud import storage

    rows = []
    client = storage.Client(project=project_id)
    for blob in client.list_blobs(bucket_name, prefix=prefix):
        if not blob.name.endswith(".jsonl"):
            continue
        rows.extend(
            json.loads(line)
            for line in blob.download_as_text().splitlines()
            if line.strip()
        )
    return rows


def verify_outputs(user_rows: list[dict[str, Any]], minute_rows: list[dict[str, Any]]) -> None:
    if len(user_rows) != 4:
        raise RuntimeError(f"Expected 4 user aggregates, received {len(user_rows)}.")
    if len(minute_rows) != 10:
        raise RuntimeError(f"Expected 10 minute aggregates, received {len(minute_rows)}.")
    if sum(row["page_views"] for row in user_rows) != 120:
        raise RuntimeError("User aggregates do not preserve all 120 page views.")
    if sum(row["page_views"] for row in minute_rows) != 120:
        raise RuntimeError("Minute aggregates do not preserve all 120 page views.")
    if sum(row["bytes_sent"] for row in user_rows) != 114000:
        raise RuntimeError("Unexpected total bytes in user aggregates.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Dataflow batch output shards.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    user_rows = load_jsonl_prefix(args.project_id, args.bucket_name, "output/by-user")
    minute_rows = load_jsonl_prefix(args.project_id, args.bucket_name, "output/by-minute")
    verify_outputs(user_rows, minute_rows)
    print("Dataflow batch outputs verified:")
    print(f"  User aggregates: {len(user_rows)}")
    print(f"  Minute aggregates: {len(minute_rows)}")
    print(f"  Page views: {sum(row['page_views'] for row in user_rows)}")
    print(f"  Bytes sent: {sum(row['bytes_sent'] for row in user_rows)}")


if __name__ == "__main__":
    main()