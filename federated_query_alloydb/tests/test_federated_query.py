import unittest

from src.run_federated_query import (
    RegionPerformance,
    build_federated_query,
    validate_identifier,
    verify_results,
)


class FederatedQueryTest(unittest.TestCase):
    def test_query_joins_alloydb_with_native_bigquery_data(self) -> None:
        query = build_federated_query(
            "demo-project", "us-central1", "alloydb-federation", "analytics"
        )

        self.assertIn("EXTERNAL_QUERY", query)
        self.assertIn("'demo-project.us-central1.alloydb-federation'", query)
        self.assertIn("`demo-project.analytics.region_targets`", query)
        self.assertIn("JOIN", query)

    def test_rejects_unsafe_identifier(self) -> None:
        with self.assertRaises(ValueError):
            validate_identifier("analytics`; DROP TABLE orders")

    def test_verifies_expected_federated_totals(self) -> None:
        results = [
            RegionPerformance("Southeast", 2, 470.65, 400.00),
            RegionPerformance("Northeast", 1, 215.00, 200.00),
            RegionPerformance("Central-West", 1, 174.25, 150.00),
            RegionPerformance("South", 1, 89.50, 100.00),
        ]

        verify_results(results)

    def test_rejects_incomplete_results(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Expected 4 regional results"):
            verify_results([RegionPerformance("Southeast", 2, 470.65, 400.00)])


if __name__ == "__main__":
    unittest.main()