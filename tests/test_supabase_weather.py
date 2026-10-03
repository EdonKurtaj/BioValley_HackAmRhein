import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from risk_assessment.observed import assess_observed_data
from risk_assessment.interfaces import RouteEvidence
from risk_assessment.supabase_weather import fetch_latest_weather_snapshot


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return self.payload


class SupabaseWeatherTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc).isoformat()

    def test_fetch_uses_only_the_newest_station_timestamp_batch(self):
        rows = [
            {"station_id": "BAS", "station_name": "Basel/Binningen", "observed_at": self.now,
             "metric": "tre200s0", "value": 22.2, "unit": "°C"},
            {"station_id": "BAS", "station_name": "Basel/Binningen", "observed_at": self.now,
             "metric": "rre150z0", "value": 1.5, "unit": "mm/10 min"},
            {"station_id": "BAS", "station_name": "Basel/Binningen", "observed_at": self.now,
             "metric": "fu3010z1", "value": 61, "unit": "km/h"},
            {"station_id": "BAS", "observed_at": "2020-01-01T00:00:00+00:00",
             "metric": "gre000z0", "value": 999, "unit": "W/m²"},
        ]
        with patch.dict(os.environ, {"SUPABASE_URL": "https://example.supabase.co",
                                    "SUPABASE_SECRET_KEY": "test.secret.key"}), \
                patch("risk_assessment.supabase_weather.urlopen", return_value=_Response(rows)) as request:
            snapshot = fetch_latest_weather_snapshot(Path(tempfile.gettempdir()))

        self.assertEqual(snapshot["storage"], "Supabase observations")
        self.assertEqual(snapshot["data"]["station"]["measurements"], {
            "tre200s0": 22.2, "rre150z0": 1.5, "fu3010z1": 61,
        })
        self.assertEqual(snapshot["data"]["station"]["observed_at_utc"], self.now)
        request.assert_called_once()
        self.assertIn("source_id=eq.meteoswiss_basel_temperature", request.call_args.args[0].full_url)
        self.assertNotIn("test.secret.key", request.call_args.args[0].full_url)

    def test_observed_assessment_scores_supplied_supabase_weather_instead_of_local_weather(self):
        snapshot = {
            "request_ok": True,
            "storage": "Supabase observations",
            "data": {"station": {
                "station_id": "BAS", "observed_at": self.now,
                "observed_at_utc": self.now,
                "measurements": {"tre200s0": 35, "rre150z0": 1.5, "fu3010z1": 120},
            }},
        }
        with tempfile.TemporaryDirectory() as temporary:
            result = assess_observed_data(Path(temporary), RouteEvidence(exposed_handling=True),
                                          weather_snapshot=snapshot)

        weather = result["current_observations"]["weather"]
        self.assertEqual(weather["storage"], "Supabase observations")
        self.assertEqual(weather["measurements"]["rre150z0"], 1.5)
        self.assertEqual(result["manufacturing_priority_score"]["components"][0]["severity_0_to_100"], 100)

    def test_missing_credentials_are_reported_without_contacting_database(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SECRET_KEY": ""}, clear=False), \
                patch("risk_assessment.supabase_weather.urlopen") as request:
            with self.assertRaisesRegex(ValueError, "set SUPABASE_URL and SUPABASE_SECRET_KEY"):
                fetch_latest_weather_snapshot(Path(tempfile.gettempdir()))
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
