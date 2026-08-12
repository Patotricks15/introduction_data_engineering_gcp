from __future__ import annotations

import argparse
import re
from dataclasses import dataclass


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class RegionPerformance:
    region_name: str
    order_count: int
    revenue: float
    revenue_target: float


def validate_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe identifier: {value}")
    return value


def build_federated_query(
    project_id: str, region: str, connection_id: str, dataset_id: str
) -> str:
    safe_project = validate_identifier(project_id)
    safe_region = validate_identifier(region)
    safe_connection = validate_identifier(connection_id)
    safe_dataset = validate_identifier(dataset_id)
    connection = f"{safe_project}.{safe_region}.{safe_connection}"
    target_table = f"{safe_project}.{safe_dataset}.region_targets"

    return f"""
        WITH alloydb_orders AS (
          SELECT order_id, region_code, customer_name, amount
          FROM EXTERNAL_QUERY(
            '{connection}',
            '''SELECT order_id, region_code, customer_name, amount FROM orders'''
          )
        )
        SELECT
          targets.region_name,
          COUNT(*) AS order_count,
          ROUND(SUM(orders.amount), 2) AS revenue,
          targets.revenue_target
        FROM alloydb_orders AS orders
        JOIN `{target_table}` AS targets USING (region_code)
        GROUP BY targets.region_name, targets.revenue_target
        ORDER BY revenue DESC
    """.strip()


def execute_query(
    project_id: str, region: str, connection_id: str, dataset_id: str
) -> list[RegionPerformance]:
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    query = build_federated_query(project_id, region, connection_id, dataset_id)
    rows = client.query(query, location=region).result()
    return [
        RegionPerformance(
            region_name=row.region_name,
            order_count=row.order_count,
            revenue=float(row.revenue),
            revenue_target=float(row.revenue_target),
        )
        for row in rows
    ]


def verify_results(results: list[RegionPerformance]) -> None:
    if len(results) != 4:
        raise RuntimeError(f"Expected 4 regional results, found {len(results)}.")
    if sum(result.order_count for result in results) != 5:
        raise RuntimeError("Expected the federated query to return 5 total orders.")
    if round(sum(result.revenue for result in results), 2) != 949.40:
        raise RuntimeError("Expected the federated revenue to total 949.40.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run and verify an AlloyDB federated query.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--connection-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = execute_query(
        args.project_id, args.region, args.connection_id, args.dataset_id
    )
    verify_results(results)
    for result in results:
        status = "met" if result.revenue >= result.revenue_target else "below"
        print(
            f"{result.region_name}: {result.order_count} orders, "
            f"${result.revenue:.2f} revenue, target {status}"
        )


if __name__ == "__main__":
    main()