import argparse


VALID_STATUSES = ("processing", "shipped", "delivered", "cancelled")
RULE_NAMES = (
    "customer_id_required",
    "amount_positive",
    "status_valid",
    "delivery_not_before_order",
)


def quality_rule_sql() -> dict[str, str]:
    return {
        "customer_id_required": "customer_id IS NOT NULL AND trim(customer_id) <> ''",
        "amount_positive": "amount > 0",
        "status_valid": f"status IN ({', '.join(repr(value) for value in VALID_STATUSES)})",
        "delivery_not_before_order": (
            "delivery_date IS NULL OR delivery_date >= order_date"
        ),
    }


def classify_record(record: dict[str, object]) -> list[str]:
    failures = []
    if not str(record.get("customer_id") or "").strip():
        failures.append("customer_id_required")
    if float(record["amount"]) <= 0:
        failures.append("amount_positive")
    if record["status"] not in VALID_STATUSES:
        failures.append("status_valid")
    delivery_date = record.get("delivery_date")
    if delivery_date and delivery_date < record["order_date"]:
        failures.append("delivery_not_before_order")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a batch of orders with Spark.")
    parser.add_argument("--input-uri", required=True)
    parser.add_argument("--valid-table", required=True)
    parser.add_argument("--rejected-table", required=True)
    parser.add_argument("--metrics-table", required=True)
    parser.add_argument("--temporary-bucket", required=True)
    return parser.parse_args()


def write_bigquery(dataframe, table: str, temporary_bucket: str) -> None:
    dataframe.write.format("bigquery").option("table", table).option(
        "temporaryGcsBucket", temporary_bucket
    ).mode("overwrite").save()


def main() -> None:
    from pyspark.sql import SparkSession, functions, types

    args = parse_args()
    spark = SparkSession.builder.appName("batch-order-data-quality").getOrCreate()
    schema = types.StructType(
        [
            types.StructField("order_id", types.StringType(), False),
            types.StructField("customer_id", types.StringType(), True),
            types.StructField("order_date", types.StringType(), False),
            types.StructField("delivery_date", types.StringType(), True),
            types.StructField("status", types.StringType(), False),
            types.StructField("amount", types.DoubleType(), False),
            types.StructField("country_code", types.StringType(), False),
        ]
    )

    try:
        source = spark.read.option("header", True).schema(schema).csv(args.input_uri)
        typed = source.withColumn("order_date", functions.to_date("order_date")).withColumn(
            "delivery_date", functions.to_date("delivery_date")
        )
        rules = quality_rule_sql()
        failure_array = functions.array(
            *[
                functions.when(~functions.expr(expression), functions.lit(rule_name))
                for rule_name, expression in rules.items()
            ]
        )
        assessed = typed.withColumn(
            "failed_rules", functions.array_compact(failure_array)
        ).withColumn("is_valid", functions.size("failed_rules") == 0)

        valid = assessed.filter("is_valid").drop("failed_rules", "is_valid")
        rejected = assessed.filter("NOT is_valid").drop("is_valid")
        metrics = assessed.agg(
            functions.count("*").alias("total_records"),
            functions.sum(functions.col("is_valid").cast("integer")).alias("valid_records"),
            functions.sum((~functions.col("is_valid")).cast("integer")).alias(
                "rejected_records"
            ),
        ).withColumn(
            "validity_rate",
            functions.round(functions.col("valid_records") / functions.col("total_records"), 4),
        ).withColumn("assessed_at", functions.current_timestamp())

        write_bigquery(valid, args.valid_table, args.temporary_bucket)
        write_bigquery(rejected, args.rejected_table, args.temporary_bucket)
        write_bigquery(metrics, args.metrics_table, args.temporary_bucket)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()