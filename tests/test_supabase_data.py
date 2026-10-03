import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from risk_assessment.observed import assess_observed_data
from risk_assessment.interfaces import RouteEvidence
from risk_assessment.supabase_data import fetch_latest_weather_snapshot, fetch_supabase_sources
from risk_assessment.dashboard import live_dashboard


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
                patch("risk_assessment.supabase_data.urlopen", return_value=_Response(rows)) as request:
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
                patch("risk_assessment.supabase_data.urlopen") as request:
            with self.assertRaisesRegex(ValueError, "set SUPABASE_URL and SUPABASE_SECRET_KEY"):
                fetch_latest_weather_snapshot(Path(tempfile.gettempdir()))
        request.assert_not_called()


class SupabasePortTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)

    def dashboard_after_empty_import(self, measurement_age=10, available=True):
        row = {"source_id": "port_pegel_current", "station_id": "Basel-Rheinhalle", "station_name": "Basel-Rheinhalle",
               "metric": "water_level", "value": 478, "unit": "cm", "fetch_run_id": "valid-run",
               "observed_at": (self.now - timedelta(minutes=measurement_age)).isoformat()}
        latest_run = {"id": "empty-run", "request_ok": True, "fetched_at": self.now.isoformat(),
                      "error": "Normalization: missing gauge value", "raw_payload": {"tables": []}}

        def observations(_url, _key, table, query):
            self.assertEqual(table, "observations")
            rows = [row, {**row, "station_id": "Other-gauge", "station_name": "Other-gauge",
                          "value": 999, "observed_at": self.now.isoformat(), "fetch_run_id": "empty-run"}] if available else []
            for field, condition in query.items():
                if condition.startswith("eq."):
                    rows = [item for item in rows if item.get(field) == condition[3:]]
                elif condition == "not.is.null":
                    rows = [item for item in rows if item.get(field) is not None]
            rows.sort(key=lambda item: item["observed_at"], reverse=True)
            return rows[:int(query["limit"])]

        with patch("risk_assessment.supabase_data._credentials", return_value=("https://example.test", "example-key")), \
                patch("risk_assessment.supabase_data._weather_snapshot", return_value={}), \
                patch("risk_assessment.supabase_data._observations", return_value=[]), \
                patch("risk_assessment.supabase_data._latest_run", side_effect=lambda _u, _k, source: latest_run if source == "port_pegel_current" else None), \
                patch("risk_assessment.supabase_data._get_json", side_effect=observations):
            sources = fetch_supabase_sources()
        return live_dashboard(sources, now=self.now)

    def test_empty_new_import_retains_previous_valid_gauge_measurement(self):
        dashboard = self.dashboard_after_empty_import()
        gauge = next(signal for signal in dashboard["signals"] if signal["id"] == "rhine")
        self.assertEqual(gauge["value"], 478)
        self.assertEqual(gauge["freshness"], "current")
        self.assertEqual(gauge["observedAt"], (self.now - timedelta(minutes=10)).isoformat())

    def test_fresh_empty_import_does_not_refresh_old_measurement(self):
        dashboard = self.dashboard_after_empty_import(measurement_age=60)
        gauge = next(signal for signal in dashboard["signals"] if signal["id"] == "rhine")
        self.assertEqual(gauge["value"], 478)
        self.assertEqual(gauge["freshness"], "stale")
        self.assertEqual(gauge["severity"], "unknown")

    def test_no_previous_measurement_remains_unknown(self):
        dashboard = self.dashboard_after_empty_import(available=False)
        gauge = next(signal for signal in dashboard["signals"] if signal["id"] == "rhine")
        self.assertIsNone(gauge["value"])
        self.assertEqual(gauge["freshness"], "unknown")


if __name__ == "__main__":
    unittest.main()
