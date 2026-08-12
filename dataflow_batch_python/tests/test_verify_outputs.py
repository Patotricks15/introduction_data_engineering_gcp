import unittest

from src.verify_outputs import verify_outputs


class VerifyOutputsTest(unittest.TestCase):
    def test_accepts_complete_user_and_minute_perspectives(self) -> None:
        user_rows = [
            {"page_views": 30, "bytes_sent": 28500}
            for _ in range(4)
        ]
        minute_rows = [
            {"page_views": 12, "bytes_sent": 11400}
            for _ in range(10)
        ]

        verify_outputs(user_rows, minute_rows)

    def test_rejects_missing_minute_shard_data(self) -> None:
        user_rows = [{"page_views": 30, "bytes_sent": 28500} for _ in range(4)]
        with self.assertRaisesRegex(RuntimeError, "Expected 10 minute aggregates"):
            verify_outputs(user_rows, [])


if __name__ == "__main__":
    unittest.main()