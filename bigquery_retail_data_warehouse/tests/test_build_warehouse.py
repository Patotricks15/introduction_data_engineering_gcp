import tempfile
import unittest
from pathlib import Path

from src.build_warehouse import (
    SQL_STEPS,
    WarehouseMetrics,
    build_verification_query,
    render_sql,
    validate_identifier,
    verify_metrics,
)


class BuildWarehouseTest(unittest.TestCase):
    def test_sql_steps_cover_the_four_labs_in_order(self) -> None:
        self.assertEqual(
            SQL_STEPS,
            (
                "01_load_nested_json.sql",
                "02_build_dimensions.sql",
                "03_build_partitioned_facts.sql",
                "04_build_reporting.sql",
            ),
        )

    def test_renders_validated_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "query.sql"
            path.write_text(
                "SELECT * FROM `{project_id}.{dataset_id}.orders`", encoding="utf-8"
            )

            query = render_sql(path, "demo-project-123", "retail_warehouse")

        self.assertIn("`demo-project-123.retail_warehouse.orders`", query)

    def test_rejects_unsafe_identifier(self) -> None:
        with self.assertRaises(ValueError):
            validate_identifier("warehouse`; DROP TABLE orders")

    def test_verification_checks_partition_metadata(self) -> None:
        query = build_verification_query("demo-project-123", "retail_warehouse")

        self.assertIn("INFORMATION_SCHEMA.PARTITIONS", query)
        self.assertIn("table_name = 'fact_orders'", query)

    def test_accepts_expected_challenge_metrics(self) -> None:
        verify_metrics(WarehouseMetrics(4, 6, 6, 9, 6, 4))

    def test_rejects_incomplete_warehouse(self) -> None:
        with self.assertRaises(RuntimeError):
            verify_metrics(WarehouseMetrics(4, 6, 5, 9, 6, 4))


if __name__ == "__main__":
    unittest.main()