import json
import random
from datetime import datetime, timezone
from typing import Any


PLAYERS = (
    {"player_id": "p-001", "display_name": "Nova", "team": "Solaris", "region": "BR", "rank": "Diamond"},
    {"player_id": "p-002", "display_name": "Cipher", "team": "Solaris", "region": "US", "rank": "Master"},
    {"player_id": "p-003", "display_name": "Kite", "team": "Northwind", "region": "GB", "rank": "Diamond"},
    {"player_id": "p-004", "display_name": "Ember", "team": "Northwind", "region": "JP", "rank": "Master"},
)
CHAT_MESSAGES = (
    "great rotation",
    "defend the objective",
    "nice play",
    "group at mid",
    "watch the flank",
)


def build_event(sequence: int, randomizer: random.Random) -> dict[str, Any]:
    player = randomizer.choice(PLAYERS)
    event_type = "chat" if sequence % 3 == 0 else "gameplay"
    event = {
        "event_id": f"event-{sequence:05d}",
        "event_time": datetime.now(timezone.utc).isoformat(),
        "match_id": f"match-{(sequence % 3) + 1:03d}",
        "player_id": player["player_id"],
        "event_type": event_type,
        "action": "message" if event_type == "chat" else randomizer.choice(("kill", "assist", "objective")),
        "score_delta": 0 if event_type == "chat" else randomizer.choice((25, 50, 100)),
        "message": randomizer.choice(CHAT_MESSAGES) if event_type == "chat" else None,
    }
    return event


def encode_event(event: dict[str, Any]) -> bytes:
    return json.dumps(event, separators=(",", ":")).encode("utf-8")


def decode_event(payload: bytes) -> dict[str, Any]:
    event = json.loads(payload.decode("utf-8"))
    required = {"event_id", "event_time", "match_id", "player_id", "event_type", "action", "score_delta"}
    missing = required - event.keys()
    if missing:
        raise ValueError(f"Missing required event fields: {sorted(missing)}")
    return event