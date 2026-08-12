import argparse
import time
from typing import Any


def build_metrics_query(table_ref: str) -> str:
    return f"""
        SELECT
          COUNT(*) AS event_count,
          COUNTIF(event_type = 'chat') AS chat_count,
          COUNT(DISTINCT player_id) AS player_count,
          COUNTIF(display_name = 'unknown') AS unknown_profiles
        FROM `{table_ref}`
    """


def wait_for_events(client: Any, table_ref: str, expected_count: int, timeout: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = next(client.query(build_metrics_query(table_ref)).result())
        metrics = dict(row.items())
        if metrics["event_count"] >= expected_count:
            if metrics["unknown_profiles"]:
                raise RuntimeError(f"Found {metrics['unknown_profiles']} events without a Bigtable profile.")
            return metrics
        time.sleep(10)
    raise TimeoutError(f"BigQuery did not receive {expected_count} events within {timeout} seconds.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify enriched e-sports events in BigQuery.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    from google.cloud import bigquery

    args = parse_args()
    table_ref = f"{args.project_id}.{args.dataset_id}.{args.table_id}"
    metrics = wait_for_events(
        bigquery.Client(project=args.project_id), table_ref, args.expected_count, args.timeout
    )
    print("E-sports streaming pipeline verified:")
    print(f"  Events: {metrics['event_count']}")
    print(f"  Chat messages: {metrics['chat_count']}")
    print(f"  Enriched players: {metrics['player_count']}")


if __name__ == "__main__":
    main()