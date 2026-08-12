import unittest

from src.verify_pipeline import build_metrics_query


class VerifyPipelineTest(unittest.TestCase):
    def test_metrics_query_checks_enrichment_and_chat(self) -> None:
        query = build_metrics_query("demo.esports.enriched_events")

        self.assertIn("`demo.esports.enriched_events`", query)
        self.assertIn("event_type = 'chat'", query)
        self.assertIn("display_name = 'unknown'", query)


if __name__ == "__main__":
    unittest.main()