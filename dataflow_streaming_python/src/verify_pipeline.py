from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class PipelineMetrics:
    corridor_count: int
    vehicle_count: int
    invalid_count: int


def validate_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe BigQuery identifier: {value}")
    return value


def build_verification_query(
    project_id: str,
    dataset_id: str,
    aggregate_table_id: str,
    dead_letter_table_id: str,
) -> str:
    project = validate_identifier(project_id)
    dataset = validate_identifier(dataset_id)
    aggregate_table = validate_identifier(aggregate_table_id)
    dead_letter_table = validate_identifier(dead_letter_table_id)
    return f"""
        WITH latest_snapshots AS (
          SELECT corridor, MAX(vehicle_count) AS vehicle_count
          FROM `{project}.{dataset}.{aggregate_table}`
          WHERE window_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 MINUTE)
          GROUP BY corridor
        )
        SELECT
          COUNT(*) AS corridor_count,
          COALESCE(SUM(vehicle_count), 0) AS vehicle_count,
          (SELECT COUNT(*) FROM `{project}.{dataset}.{dead_letter_table}`) AS invalid_count
        FROM latest_snapshots
    """.strip()


def verify_pipeline(
    project_id: str,
    dataset_id: str,
    aggregate_table_id: str,
    dead_letter_table_id: str,
    expected_events: int,
    attempts: int = 30,
    poll_seconds: float = 10,
) -> PipelineMetrics:
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    query = build_verification_query(
        project_id, dataset_id, aggregate_table_id, dead_letter_table_id
    )
    last_metrics = PipelineMetrics(0, 0, 0)
    for _ in range(attempts):
        row = next(iter(client.query(query).result()))
        last_metrics = PipelineMetrics(
            corridor_count=row.corridor_count,
            vehicle_count=row.vehicle_count,
            invalid_count=row.invalid_count,
        )
        if (
            last_metrics.corridor_count == 3
            and last_metrics.vehicle_count == expected_events
            and last_metrics.invalid_count >= 1
        ):
            return last_metrics
        time.sleep(poll_seconds)
    raise TimeoutError(
        "Expected 3 corridors, "
        f"{expected_events} vehicles, and a dead-letter row; found {last_metrics}."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify streaming Dataflow output.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--aggregate-table-id", required=True)
    parser.add_argument("--dead-letter-table-id", required=True)
    parser.add_argument("--expected-events", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = verify_pipeline(
        args.project_id,
        args.dataset_id,
        args.aggregate_table_id,
        args.dead_letter_table_id,
        args.expected_events,
    )
    print(
        f"Verified {metrics.vehicle_count} vehicles across "
        f"{metrics.corridor_count} corridors and {metrics.invalid_count} invalid event(s)."
    )


if __name__ == "__main__":
    main()