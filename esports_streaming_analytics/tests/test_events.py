import random
import unittest

from src.events import build_event, decode_event, encode_event
from src.seed_bigtable import profile_cells


class EventsTest(unittest.TestCase):
    def test_event_round_trip_preserves_streaming_contract(self) -> None:
        event = build_event(3, random.Random(42))

        decoded = decode_event(encode_event(event))

        self.assertEqual(decoded["event_id"], "event-00003")
        self.assertEqual(decoded["event_type"], "chat")
        self.assertEqual(decoded["score_delta"], 0)
        self.assertIsNotNone(decoded["message"])

    def test_bigtable_profile_uses_one_column_family(self) -> None:
        cells = profile_cells(
            {"display_name": "Nova", "team": "Solaris", "region": "BR", "rank": "Diamond"}
        )

        self.assertEqual(len(cells), 4)
        self.assertTrue(all(column.startswith(b"profile:") for column in cells))
        self.assertEqual(cells[b"profile:team"], b"Solaris")

    def test_rejects_event_missing_required_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "player_id"):
            decode_event(b'{"event_id":"broken"}')


if __name__ == "__main__":
    unittest.main()