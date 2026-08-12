import argparse

from google.cloud import bigquery


def verify_lakehouse(
    project_id: str,
    dataset_id: str,
    customer_table_id: str,
    invoice_table_id: str,
    expected_connection_id: str,
) -> None:
    client = bigquery.Client(project=project_id)
    customer_table = f"{project_id}.{dataset_id}.{customer_table_id}"
    invoice_table = f"{project_id}.{dataset_id}.{invoice_table_id}"

    for table_id in (customer_table, invoice_table):
        table = client.get_table(table_id)
        configuration = table.external_data_configuration
        if configuration is None or configuration.connection_id != expected_connection_id:
            raise RuntimeError(f"{table_id} is not using {expected_connection_id}.")

    customer_result = next(
        iter(
            client.query(
                f"SELECT COUNT(*) AS row_count "
                f"FROM `{customer_table}`"
            ).result()
        )
    )
    invoice_result = next(
        iter(
            client.query(
                f"SELECT COUNT(*) AS row_count, ROUND(SUM(total), 2) AS revenue "
                f"FROM `{invoice_table}`"
            ).result()
        )
    )

    if customer_result.row_count == 0 or invoice_result.row_count == 0:
        raise RuntimeError("Lakehouse queries returned no rows.")

    print(
        f"Verified {customer_result.row_count} customers and "
        f"{invoice_result.row_count} invoices with total revenue "
        f"{invoice_result.revenue}."
    )
    print("Both external tables use the expected Cloud Resource connection.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify the Lakehouse tables.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--customer-table-id", required=True)
    parser.add_argument("--invoice-table-id", required=True)
    parser.add_argument("--connection-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    verify_lakehouse(
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        customer_table_id=args.customer_table_id,
        invoice_table_id=args.invoice_table_id,
        expected_connection_id=args.connection_id,
    )


if __name__ == "__main__":
    main()