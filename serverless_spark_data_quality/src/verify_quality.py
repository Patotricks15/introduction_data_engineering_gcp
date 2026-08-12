import argparse
from dataclasses import dataclass
from typing import Any


EXPECTED_RULES = {
    "customer_id_required",
    "amount_positive",
    "status_valid",
    "delivery_not_before_order",
}


@dataclass(frozen=True)
class QualitySummary:
    total_records: int
    valid_records: int
    rejected_records: int
    validity_rate: float


def build_summary_query(project_id: str, dataset_id: str) -> str:
    return f"""
        SELECT
          (SELECT COUNT(*) FROM `{project_id}.{dataset_id}.valid_orders`) +
            (SELECT COUNT(*) FROM `{project_id}.{dataset_id}.rejected_orders`) AS total_records,
          (SELECT COUNT(*) FROM `{project_id}.{dataset_id}.valid_orders`) AS valid_records,
          (SELECT COUNT(*) FROM `{project_id}.{dataset_id}.rejected_orders`) AS rejected_records,
          (SELECT validity_rate FROM `{project_id}.{dataset_id}.quality_metrics` LIMIT 1)
            AS validity_rate
    """


def build_rule_query(project_id: str, dataset_id: str) -> str:
    return f"""
        SELECT DISTINCT failed_rule
        FROM `{project_id}.{dataset_id}.rejected_orders`, UNNEST(failed_rules) AS failed_rule
    """


def verify_quality(summary: QualitySummary, failed_rules: set[str]) -> None:
    expected = QualitySummary(10, 6, 4, 0.6)
    if summary != expected:
        raise RuntimeError(f"Expected quality summary {expected}, received {summary}.")
    if failed_rules != EXPECTED_RULES:
        raise RuntimeError(
            f"Expected failed rules {sorted(EXPECTED_RULES)}, received {sorted(failed_rules)}."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Spark data-quality outputs.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    return parser.parse_args()


def main() -> None:
    from google.cloud import bigquery

    args = parse_args()
    client = bigquery.Client(project=args.project_id)
    row: Any = next(client.query(build_summary_query(args.project_id, args.dataset_id)).result())
    summary = QualitySummary(
        total_records=row.total_records,
        valid_records=row.valid_records,
        rejected_records=row.rejected_records,
        validity_rate=float(row.validity_rate),
    )
    rule_rows = client.query(build_rule_query(args.project_id, args.dataset_id)).result()
    failed_rules = {row.failed_rule for row in rule_rows}
    verify_quality(summary, failed_rules)
    print("Batch data quality verified:")
    print(f"  Total records: {summary.total_records}")
    print(f"  Valid records: {summary.valid_records}")
    print(f"  Rejected records: {summary.rejected_records}")
    print(f"  Validity rate: {summary.validity_rate:.0%}")
    print(f"  Rules exercised: {', '.join(sorted(failed_rules))}")


if __name__ == "__main__":
    main()