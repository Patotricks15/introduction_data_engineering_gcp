import argparse
import csv
import io
import json
from typing import Any
from urllib.request import urlopen


TIPS_CSV_URL = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv"


def parse_tip_records(csv_text: str) -> list[dict[str, Any]]:
    records = []
    for row_id, row in enumerate(csv.DictReader(io.StringIO(csv_text)), start=1):
        records.append(
            {
                "tip_id": row_id,
                "total_bill": float(row["total_bill"]),
                "tip": float(row["tip"]),
                "sex": row["sex"],
                "smoker": row["smoker"],
                "day": row["day"],
                "time": row["time"],
                "party_size": int(row["size"]),
            }
        )
    return records


def download_tip_records() -> list[dict[str, Any]]:
    with urlopen(TIPS_CSV_URL, timeout=30) as response:
        csv_text = response.read().decode("utf-8")
    return parse_tip_records(csv_text)


def create_iceberg_table(
    project_id: str,
    bucket_name: str,
    catalog_path: str,
) -> str:
    import pyarrow as pa
    from pyiceberg.catalog import load_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import DoubleType, IntegerType, NestedField, StringType

    catalog = load_catalog(
        "demo",
        type="sql",
        uri=f"sqlite:///{catalog_path}",
        warehouse=f"gs://{bucket_name}/warehouse",
        **{
            "gcp.project-id": project_id,
            "py-io-impl": "pyiceberg.io.pyarrow.PyArrowFileIO",
        },
    )
    catalog.create_namespace_if_not_exists("restaurant")
    schema = Schema(
        NestedField(1, "tip_id", IntegerType(), required=True),
        NestedField(2, "total_bill", DoubleType(), required=True),
        NestedField(3, "tip", DoubleType(), required=True),
        NestedField(4, "sex", StringType(), required=True),
        NestedField(5, "smoker", StringType(), required=True),
        NestedField(6, "day", StringType(), required=True),
        NestedField(7, "time", StringType(), required=True),
        NestedField(8, "party_size", IntegerType(), required=True),
    )
    table = catalog.create_table_if_not_exists("restaurant.tips", schema=schema)
    records = download_tip_records()
    arrow_schema = pa.schema(
        [
            pa.field("tip_id", pa.int32(), nullable=False),
            pa.field("total_bill", pa.float64(), nullable=False),
            pa.field("tip", pa.float64(), nullable=False),
            pa.field("sex", pa.string(), nullable=False),
            pa.field("smoker", pa.string(), nullable=False),
            pa.field("day", pa.string(), nullable=False),
            pa.field("time", pa.string(), nullable=False),
            pa.field("party_size", pa.int32(), nullable=False),
        ]
    )
    table.overwrite(pa.Table.from_pylist(records, schema=arrow_schema))
    return table.metadata_location


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an Iceberg table in Cloud Storage.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--catalog-path", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata_location = create_iceberg_table(
        args.project_id,
        args.bucket_name,
        args.catalog_path,
    )
    with open(args.output, "w", encoding="utf-8") as output_file:
        json.dump({"metadata_location": metadata_location}, output_file)
    print(f"Created Iceberg table with metadata at {metadata_location}")


if __name__ == "__main__":
    main()