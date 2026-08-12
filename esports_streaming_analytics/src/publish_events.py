import argparse
import random
import time

from src.events import build_event, encode_event


def publish_events(project_id: str, topic_id: str, event_count: int, interval: float) -> int:
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    randomizer = random.Random(42)
    for sequence in range(1, event_count + 1):
        event = build_event(sequence, randomizer)
        publisher.publish(
            topic_path,
            encode_event(event),
            event_type=event["event_type"],
            match_id=event["match_id"],
        ).result(timeout=60)
        if sequence < event_count:
            time.sleep(interval)
    return event_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish synthetic e-sports events.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--event-count", type=int, default=30)
    parser.add_argument("--interval", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = publish_events(args.project_id, args.topic_id, args.event_count, args.interval)
    print(f"Published {count} e-sports events.")


if __name__ == "__main__":
    main()