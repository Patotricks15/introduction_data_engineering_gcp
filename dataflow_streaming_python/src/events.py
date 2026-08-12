from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable


CORRIDORS = ("north", "central", "south")
REQUIRED_FIELDS = {"event_id", "event_time", "corridor", "speed_kph"}


def build_events(event_count: int, start_time: datetime) -> list[dict[str, Any]]:
    if event_count <= 0:
        raise ValueError("event_count must be positive")
    if start_time.tzinfo is None:
        raise ValueError("start_time must include timezone information")

    randomizer = random.Random(42)
    return [
        {
            "event_id": f"traffic-{sequence:04d}",
            "event_time": (start_time + timedelta(seconds=sequence - 1)).isoformat(),
            "corridor": CORRIDORS[(sequence - 1) % len(CORRIDORS)],
            "speed_kph": randomizer.randint(28, 92),
        }
        for sequence in range(1, event_count + 1)
    ]


def parse_event(payload: bytes) -> dict[str, Any]:
    event = json.loads(payload.decode("utf-8"))
    missing = REQUIRED_FIELDS - event.keys()
    if missing:
        raise ValueError(f"Missing fields: {sorted(missing)}")
    if event["corridor"] not in CORRIDORS:
        raise ValueError(f"Unknown corridor: {event['corridor']}")
    if not isinstance(event["speed_kph"], int) or event["speed_kph"] < 0:
        raise ValueError("speed_kph must be a non-negative integer")
    datetime.fromisoformat(event["event_time"].replace("Z", "+00:00"))
    return event


def aggregate_events(events: Iterable[dict[str, Any]]) -> dict[str, dict[str, float]]:
    values: dict[str, list[int]] = {}
    for event in events:
        values.setdefault(event["corridor"], []).append(event["speed_kph"])
    return {
        corridor: {
            "vehicle_count": len(speeds),
            "average_speed_kph": round(sum(speeds) / len(speeds), 2),
            "max_speed_kph": max(speeds),
        }
        for corridor, speeds in values.items()
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)