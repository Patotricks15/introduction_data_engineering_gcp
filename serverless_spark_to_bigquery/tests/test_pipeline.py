import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.prepare_data import download_tips
from src.verify_load import LoadMetrics, build_metrics_query, verify_metrics


class PipelineTest(unittest.TestCase):
    @patch("src.prepare_data.urllib.request.urlopen")
    def test_download_tips_validates_and_counts_rows(self, urlopen) -> None:
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = (
            b"total_bill,tip,sex,smoker,day,time,size\n"
            b"16.99,1.01,Female,No,Sun,Dinner,2\n"
            b"10.34,1.66,Male,No,Sun,Dinner,3\n"
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "tips.csv"
            row_count = download_tips(destination)

        self.assertEqual(row_count, 2)

    def test_metrics_query_uses_fully_qualified_table(self) -> None:
        query = build_metrics_query("demo-project", "analytics", "tips")

        self.assertIn("`demo-project.analytics.tips`", query)
        self.assertIn("AVG(tip_percentage)", query)

    def test_verify_metrics_accepts_expected_output(self) -> None:
        verify_metrics(LoadMetrics(244, 4827.77, 16.08))

    def test_verify_metrics_rejects_incomplete_load(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Expected 244 rows"):
            verify_metrics(LoadMetrics(243, 4827.77, 16.08))


if __name__ == "__main__":
    unittest.main()