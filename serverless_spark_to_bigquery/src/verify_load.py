from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class LoadMetrics:
    row_count: int
    total_bill: float
    average_tip_percentage: float


def build_metrics_query(project_id: str, dataset_id: str, table_id: str) -> str:
    table = f"{project_id}.{dataset_id}.{table_id}"
    return f"""
        SELECT
          COUNT(*) AS row_count,
          ROUND(SUM(total_bill), 2) AS total_bill,
          ROUND(AVG(tip_percentage), 2) AS average_tip_percentage
        FROM `{table}`
    """.strip()


def fetch_metrics(project_id: str, dataset_id: str, table_id: str) -> LoadMetrics:
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    row = next(iter(client.query(build_metrics_query(project_id, dataset_id, table_id)).result()))
    return LoadMetrics(
        row_count=row.row_count,
        total_bill=float(row.total_bill),
        average_tip_percentage=float(row.average_tip_percentage),
    )


def verify_metrics(metrics: LoadMetrics) -> None:
    if metrics.row_count != 244:
        raise RuntimeError(f"Expected 244 rows, found {metrics.row_count}.")
    if metrics.total_bill != 4827.77:
        raise RuntimeError(f"Expected total bill 4827.77, found {metrics.total_bill}.")
    if not 15.0 < metrics.average_tip_percentage < 17.0:
        raise RuntimeError(
            "Expected average tip percentage between 15 and 17, "
            f"found {metrics.average_tip_percentage}."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the Spark BigQuery load.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = fetch_metrics(args.project_id, args.dataset_id, args.table_id)
    verify_metrics(metrics)
    print(
        "Verified Spark output: "
        f"{metrics.row_count} rows, ${metrics.total_bill:.2f} total bill, "
        f"{metrics.average_tip_percentage:.2f}% average tip."
    )


if __name__ == "__main__":
    main()