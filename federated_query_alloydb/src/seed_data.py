from __future__ import annotations

import argparse
import os


ALLOYDB_ORDERS = (
    (1001, "BR-SE", "Ada Lovelace", 149.90),
    (1002, "BR-S", "Grace Hopper", 89.50),
    (1003, "BR-NE", "Katherine Johnson", 215.00),
    (1004, "BR-SE", "Margaret Hamilton", 320.75),
    (1005, "BR-CO", "Dorothy Vaughan", 174.25),
)

REGION_TARGETS = [
    {"region_code": "BR-SE", "region_name": "Southeast", "revenue_target": "400.00"},
    {"region_code": "BR-S", "region_name": "South", "revenue_target": "100.00"},
    {"region_code": "BR-NE", "region_name": "Northeast", "revenue_target": "200.00"},
    {"region_code": "BR-CO", "region_name": "Central-West", "revenue_target": "150.00"},
]


def initialize_alloydb() -> None:
    import psycopg

    with psycopg.connect(
        host=os.environ["PGHOST"],
        port=5432,
        dbname="postgres",
        user="federated_user",
        password=os.environ["PGPASSWORD"],
        sslmode="require",
        connect_timeout=30,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    order_id BIGINT PRIMARY KEY,
                    region_code TEXT NOT NULL,
                    customer_name TEXT NOT NULL,
                    amount NUMERIC(10, 2) NOT NULL
                )
                """
            )
            cursor.executemany(
                """
                INSERT INTO orders (order_id, region_code, customer_name, amount)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (order_id) DO UPDATE SET
                    region_code = EXCLUDED.region_code,
                    customer_name = EXCLUDED.customer_name,
                    amount = EXCLUDED.amount
                """,
                ALLOYDB_ORDERS,
            )


def initialize_bigquery(project_id: str, dataset_id: str) -> None:
    from google.cloud import bigquery

    client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{dataset_id}.region_targets"
    errors = client.insert_rows_json(table_id, REGION_TARGETS)
    if errors:
        raise RuntimeError(f"Could not seed BigQuery reference data: {errors}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed AlloyDB and BigQuery demo data.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    initialize_alloydb()
    initialize_bigquery(args.project_id, args.dataset_id)
    print("Seeded 5 AlloyDB orders and 4 BigQuery region targets.")


if __name__ == "__main__":
    main()