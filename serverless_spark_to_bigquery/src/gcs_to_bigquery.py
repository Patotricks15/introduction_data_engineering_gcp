from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load a CSV file from Cloud Storage into BigQuery with Spark."
    )
    parser.add_argument("--input-uri", required=True)
    parser.add_argument("--output-table", required=True)
    parser.add_argument("--temporary-bucket", required=True)
    return parser.parse_args()


def main() -> None:
    from pyspark.sql import SparkSession, functions

    args = parse_args()
    spark = SparkSession.builder.appName("gcs-to-bigquery-template").getOrCreate()

    try:
        source = spark.read.option("header", True).option("inferSchema", True).csv(args.input_uri)
        transformed = source.withColumn(
            "tip_percentage",
            functions.round((functions.col("tip") / functions.col("total_bill")) * 100, 2),
        )
        transformed.write.format("bigquery").option("table", args.output_table).option(
            "temporaryGcsBucket", args.temporary_bucket
        ).mode("overwrite").save()
    finally:
        spark.stop()


if __name__ == "__main__":
    main()