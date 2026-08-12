import argparse
import time
from typing import Any


def wait_for_rows(
    client: Any,
    table_ref: str,
    minimum_rows: int,
    timeout_seconds: int,
    poll_interval: int = 10,
) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    query = f"""
        SELECT city, COUNT(*) AS event_count, MAX(observed_at) AS latest_observation
        FROM `{table_ref}`
        GROUP BY city
        ORDER BY city
    """
    while time.monotonic() < deadline:
        rows = [dict(row.items()) for row in client.query(query).result()]
        if sum(row["event_count"] for row in rows) >= minimum_rows:
            return rows
        time.sleep(poll_interval)
    raise TimeoutError(
        f"BigQuery did not receive {minimum_rows} events within {timeout_seconds} seconds."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify streamed weather rows in BigQuery.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--minimum-rows", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    from google.cloud import bigquery

    args = parse_args()
    table_ref = f"{args.project_id}.{args.dataset_id}.{args.table_id}"
    rows = wait_for_rows(
        bigquery.Client(project=args.project_id),
        table_ref,
        args.minimum_rows,
        args.timeout,
    )
    print("Streaming pipeline verified:")
    for row in rows:
        print(
            f"  {row['city']}: {row['event_count']} events, "
            f"latest at {row['latest_observation']}"
        )


if __name__ == "__main__":
    main()