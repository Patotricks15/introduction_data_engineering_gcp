import argparse
from typing import Any


EXPECTED_ROW_COUNT = 244
EXPECTED_TOTAL_BILL = 4827.77


def build_summary_query(table_ref: str) -> str:
    return f"""
        SELECT
          COUNT(*) AS row_count,
          ROUND(SUM(total_bill), 2) AS total_bill,
          ROUND(SUM(tip), 2) AS total_tips,
          COUNT(DISTINCT day) AS service_days
        FROM `{table_ref}`
    """


def verify_summary(summary: dict[str, Any]) -> None:
    if summary["row_count"] != EXPECTED_ROW_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_ROW_COUNT} rows, received {summary['row_count']}."
        )
    if float(summary["total_bill"]) != EXPECTED_TOTAL_BILL:
        raise ValueError(
            f"Expected total bill {EXPECTED_TOTAL_BILL}, received {summary['total_bill']}."
        )
    if summary["service_days"] != 4:
        raise ValueError(f"Expected 4 service days, received {summary['service_days']}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query and verify the Iceberg table.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", required=True)
    return parser.parse_args()


def main() -> None:
    from google.cloud import bigquery

    args = parse_args()
    table_ref = f"{args.project_id}.{args.dataset_id}.{args.table_id}"
    row = next(bigquery.Client(project=args.project_id).query(build_summary_query(table_ref)).result())
    summary = dict(row.items())
    verify_summary(summary)
    print("External Iceberg table verified:")
    print(f"  Rows: {summary['row_count']}")
    print(f"  Total bill: {summary['total_bill']}")
    print(f"  Total tips: {summary['total_tips']}")
    print(f"  Service days: {summary['service_days']}")


if __name__ == "__main__":
    main()