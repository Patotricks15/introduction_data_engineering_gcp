import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.prepare_data import download_tips
from src.run_pipeline import wait_for_run
from src.verify_output import OutputSummary, build_query, verify_summary


class ExecutionTest(unittest.TestCase):
    @patch("src.prepare_data.urllib.request.urlopen")
    def test_download_requires_complete_public_dataset(self, urlopen) -> None:
        header = b"total_bill,tip,sex,smoker,day,time,size\n"
        row = b"16.99,1.01,Female,No,Sun,Dinner,2\n"
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = header + row * 244

        with tempfile.TemporaryDirectory() as temporary_directory:
            count = download_tips(Path(temporary_directory) / "tips.csv")

        self.assertEqual(count, 244)

    @patch("src.run_pipeline.time.sleep")
    @patch("src.run_pipeline.time.monotonic", side_effect=[0, 1, 2])
    @patch("src.run_pipeline.cdap_request")
    def test_waits_until_cdap_run_completes(
        self, cdap_request, monotonic, sleep
    ) -> None:
        cdap_request.side_effect = [
            [{"runid": "run-1", "status": "RUNNING"}],
            [{"runid": "run-1", "status": "COMPLETED"}],
        ]

        result = wait_for_run("https://example/api", "tips-etl", "token", 60)

        self.assertEqual(result["status"], "COMPLETED")
        sleep.assert_called_once_with(20)

    def test_verifies_curated_bigquery_output(self) -> None:
        query = build_query("demo", "fusion", "tips_curated")

        self.assertIn("`demo.fusion.tips_curated`", query)
        self.assertIn("MAX(party_size)", query)
        verify_summary(OutputSummary(244, 4827.77, 6))


if __name__ == "__main__":
    unittest.main()