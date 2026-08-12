from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

from src.events import build_events


def publish_events(
    project_id: str,
    topic_id: str,
    event_count: int,
    interval_seconds: float,
) -> int:
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    window_start = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    for index, event in enumerate(build_events(event_count, window_start)):
        publisher.publish(
            topic_path,
            json.dumps(event).encode("utf-8"),
            corridor=event["corridor"],
        ).result(timeout=60)
        if index < event_count - 1 and interval_seconds > 0:
            time.sleep(interval_seconds)

    publisher.publish(topic_path, b'{"event_id":"invalid-demo"}').result(timeout=60)
    return event_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish synthetic traffic events.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--event-count", type=int, default=30)
    parser.add_argument("--interval-seconds", type=float, default=0.1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    published = publish_events(
        args.project_id,
        args.topic_id,
        args.event_count,
        args.interval_seconds,
    )
    print(f"Published {published} valid traffic events and 1 invalid demo event.")


if __name__ == "__main__":
    main()