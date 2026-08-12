import unittest
from unittest.mock import Mock, patch

from src.verify_pipeline import wait_for_rows


class WaitForRowsTest(unittest.TestCase):
    @patch("src.verify_pipeline.time.sleep")
    @patch("src.verify_pipeline.time.monotonic", side_effect=[0, 1, 2])
    def test_retries_until_minimum_row_count_is_reached(
        self, mock_monotonic, mock_sleep
    ) -> None:
        client = Mock()
        client.query.return_value.result.side_effect = [
            [{"city": "London", "event_count": 1}],
            [
                {"city": "London", "event_count": 2},
                {"city": "Tokyo", "event_count": 2},
            ],
        ]

        rows = wait_for_rows(client, "project.dataset.table", 4, 30, 1)

        self.assertEqual(sum(row["event_count"] for row in rows), 4)
        self.assertEqual(client.query.call_count, 2)
        mock_sleep.assert_called_once_with(1)