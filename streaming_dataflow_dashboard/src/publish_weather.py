import argparse
import json
import time
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import urlopen


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CITIES = (
    {"city": "Sao Paulo", "country": "Brazil", "latitude": -23.55, "longitude": -46.63},
    {"city": "New York", "country": "United States", "latitude": 40.71, "longitude": -74.01},
    {"city": "London", "country": "United Kingdom", "latitude": 51.51, "longitude": -0.13},
    {"city": "Tokyo", "country": "Japan", "latitude": 35.68, "longitude": 139.69},
    {"city": "Sydney", "country": "Australia", "latitude": -33.87, "longitude": 151.21},
)


def fetch_current_weather(
    city: dict[str, Any],
    http_get: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    query = urlencode(
        {
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "current": (
                "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            ),
            "timezone": "UTC",
        }
    )
    with http_get(f"{OPEN_METEO_URL}?{query}", timeout=30) as response:
        payload = json.load(response)
    return build_event(city, payload["current"])


def build_event(city: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    observed_at = current["time"]
    if not observed_at.endswith("Z"):
        observed_at = f"{observed_at}:00Z" if len(observed_at) == 16 else f"{observed_at}Z"

    return {
        "observed_at": observed_at,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "city": city["city"],
        "country": city["country"],
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "temperature_c": current["temperature_2m"],
        "relative_humidity": current["relative_humidity_2m"],
        "wind_speed_kmh": current["wind_speed_10m"],
        "weather_code": current["weather_code"],
    }


def publish_weather(project_id: str, topic_id: str, cycles: int, interval: int) -> int:
    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    published_count = 0

    for cycle in range(cycles):
        futures = []
        for city in CITIES:
            event = fetch_current_weather(city)
            data = json.dumps(event, separators=(",", ":")).encode("utf-8")
            futures.append(publisher.publish(topic_path, data, city=event["city"]))
        for future in futures:
            future.result(timeout=60)
            published_count += 1
        print(f"Published cycle {cycle + 1}/{cycles} ({published_count} events total).")
        if cycle < cycles - 1:
            time.sleep(interval)

    return published_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish live weather events to Pub/Sub.")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--topic-id", required=True)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--interval", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    count = publish_weather(args.project_id, args.topic_id, args.cycles, args.interval)
    print(f"Finished publishing {count} weather events.")


if __name__ == "__main__":
    main()