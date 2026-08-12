import json
import tempfile
import unittest
from pathlib import Path

from apache_beam.testing.test_pipeline import TestPipeline
from apache_beam.testing.util import assert_that, equal_to

from src.batch_pipeline import build_pipeline
from src.prepare_data import write_jsonl


class BatchPipelineTest(unittest.TestCase):
    def test_branches_into_exact_user_and_minute_aggregates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "traffic.jsonl"
            write_jsonl(source, 24)

            with TestPipeline() as pipeline:
                events = (
                    pipeline
                    | "Read Test Traffic" >> __import__("apache_beam").io.ReadFromText(str(source))
                    | "Decode Test Traffic" >> __import__("apache_beam").Map(json.loads)
                )
                user_totals = (
                    events
                    | "Test User Pairs" >> __import__("apache_beam").Map(
                        lambda event: (event["user_id"], event["bytes_sent"])
                    )
                    | "Test User Aggregation" >> __import__("apache_beam").CombinePerKey(sum)
                )
                minute_counts = (
                    events
                    | "Test Minute Pairs" >> __import__("apache_beam").Map(
                        lambda event: (event["event_time"][:16], 1)
                    )
                    | "Test Minute Aggregation" >> __import__("apache_beam").CombinePerKey(sum)
                )

                assert_that(
                    user_totals,
                    equal_to(
                        [
                            ("user-101", 5000),
                            ("user-102", 5600),
                            ("user-103", 5200),
                            ("user-104", 5800),
                        ]
                    ),
                    label="Assert User Totals",
                )
                assert_that(
                    minute_counts,
                    equal_to([("2026-08-12T12:00", 12), ("2026-08-12T12:01", 12)]),
                    label="Assert Minute Counts",
                )

    def test_full_pipeline_writes_both_output_branches(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "traffic.jsonl"
            write_jsonl(source, 12)

            with TestPipeline() as pipeline:
                build_pipeline(
                    pipeline,
                    str(source),
                    str(root / "users"),
                    str(root / "minutes"),
                )

            user_files = list(root.glob("users*.jsonl"))
            minute_files = list(root.glob("minutes*.jsonl"))
            self.assertTrue(user_files)
            self.assertTrue(minute_files)
            user_rows = [json.loads(line) for path in user_files for line in path.read_text().splitlines()]
            minute_rows = [json.loads(line) for path in minute_files for line in path.read_text().splitlines()]
            self.assertEqual(len(user_rows), 4)
            self.assertEqual(len(minute_rows), 1)
            self.assertEqual(minute_rows[0]["page_views"], 12)


if __name__ == "__main__":
    unittest.main()