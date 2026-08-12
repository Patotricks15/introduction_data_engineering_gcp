import unittest

from src.verify_quality import (
    EXPECTED_RULES,
    QualitySummary,
    build_rule_query,
    build_summary_query,
    verify_quality,
)


class VerifyQualityTest(unittest.TestCase):
    def test_queries_fully_qualified_quality_tables(self) -> None:
        summary_query = build_summary_query("demo", "quality")
        rule_query = build_rule_query("demo", "quality")

        self.assertIn("`demo.quality.valid_orders`", summary_query)
        self.assertIn("`demo.quality.rejected_orders`", rule_query)
        self.assertIn("UNNEST(failed_rules)", rule_query)

    def test_accepts_expected_quality_result(self) -> None:
        verify_quality(QualitySummary(10, 6, 4, 0.6), EXPECTED_RULES)

    def test_rejects_missing_rule_failures(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Expected failed rules"):
            verify_quality(
                QualitySummary(10, 6, 4, 0.6),
                EXPECTED_RULES - {"status_valid"},
            )


if __name__ == "__main__":
    unittest.main()