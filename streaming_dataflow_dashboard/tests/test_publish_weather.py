import unittest
from unittest.mock import patch

from src.publish_weather import build_event


class BuildEventTest(unittest.TestCase):
    @patch("src.publish_weather.datetime")
    def test_builds_bigquery_compatible_event(self, mock_datetime) -> None:
        mock_datetime.now.return_value.isoformat.return_value = "2026-08-12T12:01:00+00:00"
        city = {
            "city": "Sao Paulo",
            "country": "Brazil",
            "latitude": -23.55,
            "longitude": -46.63,
        }
        current = {
            "time": "2026-08-12T12:00",
            "temperature_2m": 22.5,
            "relative_humidity_2m": 61,
            "wind_speed_10m": 8.2,
            "weather_code": 2,
        }

        event = build_event(city, current)

        self.assertEqual(event["observed_at"], "2026-08-12T12:00:00Z")
        self.assertEqual(event["published_at"], "2026-08-12T12:01:00+00:00")
        self.assertEqual(event["city"], "Sao Paulo")
        self.assertEqual(event["temperature_c"], 22.5)
        self.assertEqual(event["relative_humidity"], 61)
        self.assertEqual(len(event), 10)


if __name__ == "__main__":
    unittest.main()