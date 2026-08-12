from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
SQL_STEPS = (
    "01_load_nested_json.sql",
    "02_build_dimensions.sql",
    "03_build_partitioned_facts.sql",
    "04_build_reporting.sql",
)


@dataclass(frozen=True)
class WarehouseMetrics:
    customer_count: int
    product_count: int
    order_count: int
    order_item_count: int
    reporting_row_count: int
    partition_count: int


def validate_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe BigQuery identifier: {value}")
    return value


def render_sql(path: Path, project_id: str, dataset_id: str) -> str:
    values = {
        "project_id": validate_identifier(project_id),
        "dataset_id": validate_identifier(dataset_id),
    }
    return path.read_text(encoding="utf-8").format(**values)


def build_verification_query(project_id: str, dataset_id: str) -> str:
    project = validate_identifier(project_id)
    dataset = validate_identifier(dataset_id)
    return f"""
        SELECT
          (SELECT COUNT(*) FROM `{project}.{dataset}.dim_customers`) AS customer_count,
                    (SELECT COUNT(*) FROM `{project}.{dataset}.dim_products`) AS product_count,
          (SELECT COUNT(*) FROM `{project}.{dataset}.fact_orders`) AS order_count,
          (SELECT COUNT(*) FROM `{project}.{dataset}.fact_order_items`) AS order_item_count,
          (SELECT COUNT(*) FROM `{project}.{dataset}.daily_sales`) AS reporting_row_count,
          (SELECT COUNT(*) FROM `{project}.{dataset}.INFORMATION_SCHEMA.PARTITIONS`
           WHERE table_name = 'fact_orders' AND partition_id IS NOT NULL) AS partition_count
    """.strip()


def parse_metrics(row: Any) -> WarehouseMetrics:
    return WarehouseMetrics(
        customer_count=int(row.customer_count),
        product_count=int(row.product_count),
        order_count=int(row.order_count),
        order_item_count=int(row.order_item_count),
        reporting_row_count=int(row.reporting_row_count),
        partition_count=int(row.partition_count),
    )


def verify_metrics(metrics: WarehouseMetrics) -> None:
    expected = WarehouseMetrics(4, 6, 6, 9, 6, 4)
    if metrics != expected:
        raise RuntimeError(f"Warehouse verification failed: expected {expected}, found {metrics}.")


def load_raw_orders(
    client: Any,
    project_id: str,
    dataset_id: str,
    location: str,
    data_file: Path,
) -> None:
    from google.cloud import bigquery

    table_id = (
        f"{validate_identifier(project_id)}."
        f"{validate_identifier(dataset_id)}.raw_orders"
    )
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    with data_file.open("rb") as source:
        client.load_table_from_file(
            source, table_id, job_config=job_config, location=location
        ).result()


def run_pipeline(
    project_id: str,
    location: str,
    dataset_id: str,
    sql_dir: Path,
    data_file: Path,
) -> WarehouseMetrics:
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    load_raw_orders(client, project_id, dataset_id, location, data_file)
    for filename in SQL_STEPS:
        client.query(
            render_sql(sql_dir / filename, project_id, dataset_id),
            location=location,
        ).result()

    row = next(
        iter(
            client.query(
                build_verification_query(project_id, dataset_id), location=location
            ).result()
        )
    )
    metrics = parse_metrics(row)
    verify_metrics(metrics)
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and verify a BigQuery warehouse.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--location", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--sql-dir", type=Path, required=True)
    parser.add_argument("--data-file", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metrics = run_pipeline(
        args.project_id,
        args.location,
        args.dataset_id,
        args.sql_dir,
        args.data_file,
    )
    print(
        "Warehouse verified: "
        f"{metrics.customer_count} customers, {metrics.product_count} products, "
        f"{metrics.order_count} orders, "
        f"{metrics.order_item_count} items, {metrics.reporting_row_count} reporting rows, "
        f"and {metrics.partition_count} date partitions."
    )


if __name__ == "__main__":
    main()