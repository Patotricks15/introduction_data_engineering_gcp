import unittest

from src.run_mesh import (
    QualityResult,
    api_url,
    parse_quality_result,
    validate_identifier,
    verify_challenge_results,
    verify_catalog_entry,
)


class RunMeshTest(unittest.TestCase):
    def test_parses_passing_quality_result(self) -> None:
        result = parse_quality_result(
            {
                "name": "projects/demo/locations/us-central1/dataScans/orders/jobs/1",
                "state": "SUCCEEDED",
                "dataQualityResult": {
                    "passed": True,
                    "score": 100,
                    "rowCount": "5",
                    "rules": [{"passed": True}, {"passed": True}],
                },
            }
        )

        self.assertEqual(result.row_count, 5)
        self.assertEqual(result.rule_count, 2)

    def test_rejects_failed_quality_rule(self) -> None:
        with self.assertRaises(RuntimeError):
            parse_quality_result(
                {
                    "name": "scan-job",
                    "state": "SUCCEEDED",
                    "dataQualityResult": {
                        "passed": False,
                        "score": 75,
                        "rowCount": "4",
                        "rules": [{"passed": False}],
                    },
                }
            )

    def test_accepts_expected_challenge_cardinality(self) -> None:
        verify_challenge_results(
            QualityResult("orders", 5, 100.0, True, 4),
            QualityResult("customers", 4, 100.0, True, 4),
        )

    def test_rejects_missing_quality_rule(self) -> None:
        with self.assertRaises(RuntimeError):
            verify_challenge_results(
                QualityResult("orders", 5, 100.0, True, 3),
                QualityResult("customers", 4, 100.0, True, 4),
            )

    def test_verifies_governance_aspect(self) -> None:
        verify_catalog_entry(
            {
                "aspects": {
                    "demo.us-central1.domain-governance": {
                        "data": {"domain": "sales", "quality_slo": 0.95}
                    }
                }
            },
            "sales",
        )

    def test_rejects_entry_without_aspect(self) -> None:
        with self.assertRaises(RuntimeError):
            verify_catalog_entry({}, "customers")

    def test_builds_dataplex_api_url(self) -> None:
        self.assertEqual(
            api_url("projects/demo/locations/us-central1/dataScans/orders", ":run"),
            "https://dataplex.googleapis.com/v1/projects/demo/locations/"
            "us-central1/dataScans/orders:run",
        )

    def test_rejects_unsafe_identifier(self) -> None:
        with self.assertRaises(ValueError):
            validate_identifier("sales`; DROP TABLE orders")


if __name__ == "__main__":
    unittest.main()