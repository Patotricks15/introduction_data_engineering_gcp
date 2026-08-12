import unittest

from src.verify_pipeline import build_verification_query, validate_identifier


class VerifyPipelineTest(unittest.TestCase):
    def test_query_uses_latest_snapshot_per_corridor(self) -> None:
        query = build_verification_query(
            "demo-project", "traffic", "metrics", "errors"
        )

        self.assertIn("MAX(vehicle_count)", query)
        self.assertIn("GROUP BY corridor", query)
        self.assertIn("`demo-project.traffic.errors`", query)

    def test_rejects_unsafe_identifier(self) -> None:
        with self.assertRaises(ValueError):
            validate_identifier("metrics`; DROP TABLE errors")


if __name__ == "__main__":
    unittest.main()