import unittest

from src.verify_iceberg import build_summary_query, verify_summary


class VerifyIcebergTest(unittest.TestCase):
    def test_builds_standard_sql_query_for_external_table(self) -> None:
        query = build_summary_query("demo.external_iceberg.tips_iceberg")

        self.assertIn("`demo.external_iceberg.tips_iceberg`", query)
        self.assertIn("SUM(total_bill)", query)

    def test_accepts_expected_public_dataset_summary(self) -> None:
        verify_summary(
            {
                "row_count": 244,
                "total_bill": 4827.77,
                "total_tips": 731.58,
                "service_days": 4,
            }
        )

    def test_rejects_incomplete_iceberg_table(self) -> None:
        with self.assertRaisesRegex(ValueError, "Expected 244 rows"):
            verify_summary(
                {
                    "row_count": 1,
                    "total_bill": 16.99,
                    "total_tips": 1.01,
                    "service_days": 1,
                }
            )


if __name__ == "__main__":
    unittest.main()