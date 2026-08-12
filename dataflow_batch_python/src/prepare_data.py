import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


USERS = ("user-101", "user-102", "user-103", "user-104")
PATHS = ("/", "/products", "/pricing", "/docs", "/checkout")


def generate_events(event_count: int = 120) -> list[dict[str, object]]:
    start = datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc)
    events = []
    for sequence in range(event_count):
        events.append(
            {
                "event_id": f"view-{sequence + 1:04d}",
                "event_time": (start + timedelta(seconds=sequence * 5)).isoformat(),
                "user_id": USERS[sequence % len(USERS)],
                "path": PATHS[sequence % len(PATHS)],
                "bytes_sent": 500 + ((sequence % 10) * 100),
            }
        )
    return events


def write_jsonl(destination: Path, event_count: int = 120) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as output_file:
        for event in generate_events(event_count):
            output_file.write(json.dumps(event, separators=(",", ":")) + "\n")
    return event_count


def upload_file(project_id: str, bucket_name: str, source: Path) -> str:
    from google.cloud import storage

    blob = storage.Client(project=project_id).bucket(bucket_name).blob("input/site-traffic.jsonl")
    blob.upload_from_filename(source)
    return f"gs://{bucket_name}/{blob.name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic site traffic.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bucket-name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--event-count", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = write_jsonl(args.output, args.event_count)
    uri = upload_file(args.project_id, args.bucket_name, args.output)
    print(f"Uploaded {count} site traffic events to {uri}")


if __name__ == "__main__":
    main()