import argparse
import csv
from pathlib import Path


ORDERS = (
    ("O-1001", "C-101", "2026-08-01", "2026-08-03", "delivered", "129.90", "BR"),
    ("O-1002", "C-102", "2026-08-01", "2026-08-04", "shipped", "84.50", "US"),
    ("O-1003", "C-103", "2026-08-02", "", "processing", "42.00", "GB"),
    ("O-1004", "", "2026-08-02", "2026-08-03", "delivered", "75.00", "BR"),
    ("O-1005", "C-105", "2026-08-03", "2026-08-02", "delivered", "210.00", "DE"),
    ("O-1006", "C-106", "2026-08-03", "", "cancelled", "12.00", "JP"),
    ("O-1007", "C-107", "2026-08-04", "2026-08-05", "unknown", "55.25", "AU"),
    ("O-1008", "C-108", "2026-08-04", "2026-08-06", "delivered", "-9.90", "BR"),
    ("O-1009", "C-109", "2026-08-05", "2026-08-07", "delivered", "320.40", "CA"),
    ("O-1010", "C-110", "2026-08-05", "", "processing", "18.75", "US"),
)
HEADER = (
    "order_id",
    "customer_id",
    "order_date",
    "delivery_date",
    "status",
    "amount",
    "country_code",
)


def write_orders(destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(HEADER)
        writer.writerows(ORDERS)
    return len(ORDERS)


def upload_file(project_id: str, bucket_name: str, source: Path) -> str:
    from google.cloud import storage

    client = storage.Client(project=project_id)
    blob = client.bucket(bucket_name).blob(f"input/{source.name}")
    blob.upload_from_filename(source)
    return f"gs://{bucket_name}/{blob.name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create batch order data with known defects.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    row_count = write_orders(args.output)
    uri = upload_file(args.project_id, args.bucket_name, args.output)
    print(f"Uploaded {row_count} order rows to {uri}")


if __name__ == "__main__":
    main()