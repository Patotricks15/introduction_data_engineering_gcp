import csv
import tempfile
import unittest
from pathlib import Path

from src.prepare_data import write_orders
from src.validate_orders import RULE_NAMES, classify_record, quality_rule_sql


class DataQualityTest(unittest.TestCase):
    def test_generated_batch_has_expected_quality_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "orders.csv"
            self.assertEqual(write_orders(path), 10)
            with path.open(newline="", encoding="utf-8") as csv_file:
                records = list(csv.DictReader(csv_file))

        failures = {
            record["order_id"]: classify_record(record)
            for record in records
            if classify_record(record)
        }

        self.assertEqual(len(failures), 4)
        self.assertEqual(failures["O-1004"], ["customer_id_required"])
        self.assertEqual(failures["O-1005"], ["delivery_not_before_order"])
        self.assertEqual(failures["O-1007"], ["status_valid"])
        self.assertEqual(failures["O-1008"], ["amount_positive"])

    def test_spark_expressions_cover_every_rule(self) -> None:
        self.assertEqual(tuple(quality_rule_sql()), RULE_NAMES)


if __name__ == "__main__":
    unittest.main()