from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
TERMINAL_SCAN_STATES = {"SUCCEEDED", "SUCCEEDED_WITH_ERRORS", "FAILED", "CANCELLED"}


@dataclass(frozen=True)
class QualityResult:
    scan_name: str
    row_count: int
    score: float
    passed: bool
    rule_count: int


def validate_identifier(value: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe Google Cloud identifier: {value}")
    return value


def read_json_lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def parse_quality_result(job: dict[str, Any]) -> QualityResult:
    if job.get("state") != "SUCCEEDED":
        raise RuntimeError(
            f"Data quality scan {job.get('name', '<unknown>')} ended in "
            f"{job.get('state')}: {job.get('message', '')}"
        )
    result = job.get("dataQualityResult", {})
    rules = result.get("rules", [])
    quality = QualityResult(
        scan_name=job["name"],
        row_count=int(result.get("rowCount", 0)),
        score=float(result.get("score", 0)),
        passed=bool(result.get("passed", False)),
        rule_count=len(rules),
    )
    if not quality.passed or quality.score != 100.0:
        raise RuntimeError(f"Data quality challenge failed: {quality}.")
    if not rules or any(not rule.get("passed", False) for rule in rules):
        raise RuntimeError(f"One or more rules failed in {quality.scan_name}.")
    return quality


def verify_challenge_results(
    orders: QualityResult, customers: QualityResult
) -> None:
    if (orders.row_count, orders.rule_count) != (5, 4):
        raise RuntimeError(f"Expected 5 order rows and 4 rules, found {orders}.")
    if (customers.row_count, customers.rule_count) != (4, 4):
        raise RuntimeError(f"Expected 4 customer rows and 4 rules, found {customers}.")


def verify_catalog_entry(entry: dict[str, Any], domain: str) -> None:
    aspects = entry.get("aspects", {})
    if not aspects:
        raise RuntimeError(f"Catalog entry for {domain} has no governance aspect.")
    aspect_data = next(iter(aspects.values())).get("data", {})
    if aspect_data.get("domain") != domain:
        raise RuntimeError(f"Expected domain {domain}, found aspect data {aspect_data}.")
    if float(aspect_data.get("quality_slo", 0)) < 0.95:
        raise RuntimeError(f"Catalog entry for {domain} has an insufficient quality SLO.")


def api_url(resource_name: str, suffix: str = "") -> str:
    return f"https://dataplex.googleapis.com/v1/{resource_name}{suffix}"


def run_scan(session: Any, scan_name: str, attempts: int = 60) -> QualityResult:
    response = session.post(api_url(scan_name, ":run"), json={})
    response.raise_for_status()
    job_name = response.json()["job"]["name"]

    for _ in range(attempts):
        job_response = session.get(api_url(job_name), params={"view": "FULL"})
        job_response.raise_for_status()
        job = job_response.json()
        if job.get("state") in TERMINAL_SCAN_STATES:
            return parse_quality_result(job)
        time.sleep(10)
    raise TimeoutError(f"Data quality scan did not finish: {scan_name}")


def load_domain_data(
    project_id: str,
    region: str,
    bucket_name: str,
    sales_dataset_id: str,
    customers_dataset_id: str,
    data_dir: Path,
) -> tuple[int, int]:
    from google.cloud import bigquery, storage

    orders = read_json_lines(data_dir / "orders.json")
    customers = read_json_lines(data_dir / "customers.json")

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    bucket.blob("sales/orders.json").upload_from_filename(data_dir / "orders.json")
    bucket.blob("customers/customer_profiles.json").upload_from_filename(
        data_dir / "customers.json"
    )

    bigquery_client = bigquery.Client(project=project_id)
    loads = (
        (f"{project_id}.{sales_dataset_id}.orders", orders),
        (f"{project_id}.{customers_dataset_id}.customer_profiles", customers),
    )
    for table_id, rows in loads:
        config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        bigquery_client.load_table_from_json(
            rows, table_id, location=region, job_config=config
        ).result()
    return len(orders), len(customers)


def verify_bigquery_counts(
    project_id: str,
    region: str,
    sales_dataset_id: str,
    customers_dataset_id: str,
) -> None:
    from google.cloud import bigquery

    query = f"""
        SELECT
          (SELECT COUNT(*) FROM `{project_id}.{sales_dataset_id}.orders`) AS orders,
          (SELECT COUNT(*) FROM `{project_id}.{customers_dataset_id}.customer_profiles`)
            AS customers
    """
    row = next(iter(bigquery.Client(project=project_id).query(query, location=region).result()))
    if (row.orders, row.customers) != (5, 4):
        raise RuntimeError(f"Expected 5 orders and 4 customers, found {row.orders} and {row.customers}.")


def verify_catalog(
    session: Any,
    catalog_entries: dict[str, str],
    data_products: dict[str, str],
) -> None:
    for domain in ("sales", "customers"):
        entry_name = catalog_entries[domain]
        response = session.get(api_url(entry_name), params={"view": "FULL"})
        response.raise_for_status()
        verify_catalog_entry(response.json(), domain)

        product_name = data_products[domain]
        product_response = session.get(api_url(product_name))
        product_response.raise_for_status()
        if not product_response.json().get("ownerEmails"):
            raise RuntimeError(f"Data product {domain} has no owner.")


def run(args: argparse.Namespace) -> tuple[QualityResult, QualityResult]:
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    for value in (
        args.project_id,
        args.region,
        args.sales_dataset_id,
        args.customers_dataset_id,
    ):
        validate_identifier(value)

    orders, customers = load_domain_data(
        args.project_id,
        args.region,
        args.bucket_name,
        args.sales_dataset_id,
        args.customers_dataset_id,
        args.data_dir,
    )
    if (orders, customers) != (5, 4):
        raise RuntimeError("Unexpected domain fixture cardinality.")
    verify_bigquery_counts(
        args.project_id, args.region, args.sales_dataset_id, args.customers_dataset_id
    )

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    orders_quality = run_scan(session, args.orders_scan_id)
    customers_quality = run_scan(session, args.customers_scan_id)
    verify_challenge_results(orders_quality, customers_quality)
    verify_catalog(
        session,
        json.loads(args.catalog_entries),
        json.loads(args.data_products),
    )
    return orders_quality, customers_quality


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run and verify the Knowledge Catalog data mesh.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--sales-dataset-id", required=True)
    parser.add_argument("--customers-dataset-id", required=True)
    parser.add_argument("--orders-scan-id", required=True)
    parser.add_argument("--customers-scan-id", required=True)
    parser.add_argument("--catalog-entries", required=True)
    parser.add_argument("--data-products", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    orders_quality, customers_quality = run(parse_args())
    print(
        "Data mesh challenge verified: "
        f"orders={orders_quality.row_count} rows/{orders_quality.score:.0f}% and "
        f"customers={customers_quality.row_count} rows/{customers_quality.score:.0f}%."
    )


if __name__ == "__main__":
    main()