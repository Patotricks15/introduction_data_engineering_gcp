import unittest
from unittest.mock import Mock, patch

from src.trigger_and_verify import wait_for_rows


class WaitForRowsTest(unittest.TestCase):
    @patch("src.trigger_and_verify.bigquery.Client")
    def test_waits_until_expected_row_count(self, client_class: Mock) -> None:
        client_class.return_value.get_table.side_effect = [
            Mock(num_rows=0),
            Mock(num_rows=244),
        ]

        row_count = wait_for_rows(
            "sample-project", "analytics", "tips", attempts=2, poll_seconds=0
        )

        self.assertEqual(row_count, 244)

    @patch("src.trigger_and_verify.bigquery.Client")
    def test_times_out_for_wrong_row_count(self, client_class: Mock) -> None:
        client_class.return_value.get_table.return_value.num_rows = 1

        with self.assertRaises(TimeoutError):
            wait_for_rows(
                "sample-project", "analytics", "tips", attempts=1, poll_seconds=0
            )


if __name__ == "__main__":
    unittest.main()