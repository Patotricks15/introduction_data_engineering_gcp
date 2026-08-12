import json
import unittest
from datetime import datetime, timezone

from src.events import aggregate_events, build_events, parse_event


class EventsTest(unittest.TestCase):
    def test_builds_reproducible_events_for_all_corridors(self) -> None:
        events = build_events(6, datetime(2026, 8, 12, tzinfo=timezone.utc))

        self.assertEqual(len(events), 6)
        self.assertEqual([event["corridor"] for event in events], [
            "north", "central", "south", "north", "central", "south"
        ])

    def test_parses_valid_event(self) -> None:
        event = build_events(1, datetime(2026, 8, 12, tzinfo=timezone.utc))[0]

        self.assertEqual(parse_event(json.dumps(event).encode("utf-8")), event)

    def test_rejects_unknown_corridor(self) -> None:
        payload = b'{"event_id":"1","event_time":"2026-08-12T00:00:00+00:00","corridor":"east","speed_kph":50}'

        with self.assertRaisesRegex(ValueError, "Unknown corridor"):
            parse_event(payload)

    def test_aggregates_count_average_and_max_speed(self) -> None:
        events = [
            {"corridor": "north", "speed_kph": 40},
            {"corridor": "north", "speed_kph": 60},
            {"corridor": "south", "speed_kph": 35},
        ]

        aggregates = aggregate_events(events)

        self.assertEqual(aggregates["north"], {
            "vehicle_count": 2,
            "average_speed_kph": 50.0,
            "max_speed_kph": 60,
        })
        self.assertEqual(aggregates["south"]["vehicle_count"], 1)


if __name__ == "__main__":
    unittest.main()