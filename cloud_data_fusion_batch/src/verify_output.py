import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class OutputSummary:
    row_count: int
    total_bill: float
    max_party_size: int


def build_query(project_id: str, dataset_id: str, table_id: str) -> str:
    return f"""
        SELECT
          COUNT(*) AS row_count,
          ROUND(SUM(total_bill), 2) AS total_bill,
          MAX(party_size) AS max_party_size
        FROM `{project_id}.{dataset_id}.{table_id}`
    """


def verify_summary(summary: OutputSummary) -> None:
    expected = OutputSummary(244, 4827.77, 6)
    if summary != expected:
        raise RuntimeError(f"Expected {expected}, received {summary}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the Data Fusion BigQuery output.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--table-id", required=True)
    return parser.parse_args()


def main() -> None:
    from google.cloud import bigquery

    args = parse_args()
    row = next(
        bigquery.Client(project=args.project_id)
        .query(build_query(args.project_id, args.dataset_id, args.table_id))
        .result()
    )
    summary = OutputSummary(row.row_count, float(row.total_bill), row.max_party_size)
    verify_summary(summary)
    print("Cloud Data Fusion output verified:")
    print(f"  Rows: {summary.row_count}")
    print(f"  Total bill: {summary.total_bill}")
    print(f"  Maximum party size: {summary.max_party_size}")


if __name__ == "__main__":
    main()