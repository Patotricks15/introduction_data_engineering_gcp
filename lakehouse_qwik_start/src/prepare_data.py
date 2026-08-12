import argparse
import csv
import sqlite3
import urllib.request
from pathlib import Path

CHINOOK_DATABASE_URL = (
    "https://raw.githubusercontent.com/lerocha/chinook-database/master/"
    "ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
)

EXPORTS = {
    "customer.csv": (
        "SELECT CustomerId, FirstName, LastName, Company, Address, City, State, "
        "Country, PostalCode, Phone, Fax, Email, SupportRepId "
        "FROM Customer ORDER BY CustomerId",
        [
            "customer_id",
            "first_name",
            "last_name",
            "company",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "phone",
            "fax",
            "email",
            "support_rep_id",
        ],
    ),
    "invoice.csv": (
        "SELECT InvoiceId, CustomerId, InvoiceDate, BillingAddress, BillingCity, "
        "BillingState, BillingCountry, BillingPostalCode, Total "
        "FROM Invoice ORDER BY InvoiceId",
        [
            "invoice_id",
            "customer_id",
            "invoice_date",
            "billing_address",
            "billing_city",
            "billing_state",
            "billing_country",
            "billing_postal_code",
            "total",
        ],
    ),
}


def download_database(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        destination.write_bytes(response.read())


def export_csv_files(database_path: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    exported_files = []

    with sqlite3.connect(database_path) as connection:
        for filename, (query, headers) in EXPORTS.items():
            output_path = output_dir / filename
            rows = connection.execute(query)
            with output_path.open("w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(headers)
                writer.writerows(rows)
            exported_files.append(output_path)

    return exported_files


def upload_files(project_id: str, bucket_name: str, paths: list[Path]) -> None:
    from google.cloud import storage

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    for path in paths:
        bucket.blob(path.name).upload_from_filename(path)
        print(f"Uploaded {path} to gs://{bucket_name}/{path.name}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare public Chinook data for the Lakehouse tables."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--source-url", default=CHINOOK_DATABASE_URL)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = args.data_dir / "Chinook_Sqlite.sqlite"
    print(f"Downloading the public Chinook database from {args.source_url}...")
    download_database(args.source_url, database_path)
    paths = export_csv_files(database_path, args.data_dir)
    upload_files(args.project_id, args.bucket_name, paths)


if __name__ == "__main__":
    main()