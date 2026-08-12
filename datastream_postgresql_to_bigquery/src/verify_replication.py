#!/usr/bin/env python3

import argparse
import re
import time

from google.api_core.exceptions import NotFound
from google.cloud import bigquery


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(value: str) -> str:
    """Reject values that cannot safely be used as BigQuery identifiers."""
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Invalid BigQuery identifier: {value}")
    return value


def wait_for_order(
    project_id: str,
    dataset_id: str,
    order_id: int,
    timeout_seconds: int,
    poll_seconds: int = 15,
) -> dict[str, object]:
    """Poll BigQuery until a replicated order is queryable."""
    dataset_id = validate_identifier(dataset_id)
    client = bigquery.Client(project=project_id)
    query = f"""
        SELECT order_id, customer_name, status, amount
        FROM `{project_id}.{dataset_id}.orders`
        WHERE order_id = @order_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("order_id", "INT64", order_id)
        ]
    )
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            rows = list(client.query(query, job_config=job_config).result())
            if rows:
                return dict(rows[0].items())
        except NotFound:
            pass
        time.sleep(poll_seconds)

    raise TimeoutError(
        f"Order {order_id} was not replicated within {timeout_seconds} seconds."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify PostgreSQL CDC in BigQuery.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--order-id", type=int, default=1004)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    order = wait_for_order(
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        order_id=args.order_id,
        timeout_seconds=args.timeout,
    )
    print(f"Replication verified in BigQuery: {order}")


if __name__ == "__main__":
    main()
