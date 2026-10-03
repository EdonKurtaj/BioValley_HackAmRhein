"""Weather parsing and Supabase normalization across complete and partial rows."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import api_requester
from normalize_observations import normalize
from weather_parameters import WEATHER_PARAMETERS


class WeatherObservationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.enterContext(patch.object(api_requester, "ROOT", self.root))
        self.enterContext(patch.object(api_requester, "DATA_DIR", self.root / "data"))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.source = next(source for source in api_requester.SOURCES if source["kind"] == "meteo_current")

    def fetch(self, values):
        body = ("Station/Location;Date;" + ";".join(values) + "\nBAS;202610031000;" +
                ";".join(values.values()) + "\n").encode("cp1252")
        with patch.object(api_requester, "read_response", return_value=(200, {}, body, None)):
            return api_requester.check_meteoswiss_current(self.source)

    def test_all_nine_weather_metrics_are_saved_with_units_and_time(self):
        values = dict(zip(WEATHER_PARAMETERS, ("18.0", "0", "614", "10", "3.2", "7.1", "25", "73.4", "13.2")))
        result = self.fetch(values)
        self.assertTrue(result["request_ok"])
        self.assertEqual(result["data"]["station"]["missing_measurements"], [])
        rows = normalize(result)
        self.assertEqual(len(rows), 9)
        self.assertEqual({row["metric"] for row in rows}, set(WEATHER_PARAMETERS))
        self.assertTrue(all(row["station_id"] == "BAS" for row in rows))
        self.assertTrue(all(row["observed_at"] == "2026-10-03T10:00:00+00:00" for row in rows))
        for row in rows:
            self.assertEqual(row["unit"], WEATHER_PARAMETERS[row["metric"]]["unit"])
        precipitation = next(row for row in rows if row["metric"] == "rre150z0")
        self.assertEqual(precipitation["value"], 0)
        self.assertEqual(precipitation["dimensions"], {"aggregation": "sum", "interval_minutes": 10})
        saved = json.loads((self.root / "data" / self.source["id"] / "latest.json").read_text())
        self.assertEqual(saved["data"]["station"]["measurements"], result["data"]["station"]["measurements"])

    def test_missing_and_invalid_weather_values_do_not_discard_valid_measurements(self):
        result = self.fetch({"tre200s0": "18", "rre150z0": "0", "gre000z0": "NaN", "sre000z0": "-", "fu3010z0": ""})
        self.assertTrue(result["request_ok"])
        self.assertEqual({row["metric"] for row in normalize(result)}, {"tre200s0", "rre150z0"})
        self.assertEqual(result["data"]["station"]["measurements"]["gre000z0"], None)
        self.assertIn("fu3010z1", result["data"]["station"]["missing_measurements"])
        json.dumps(result, allow_nan=False)

    def test_other_weather_measurements_are_saved_when_temperature_is_missing(self):
        result = self.fetch({"ure200s0": "73.4", "fu3010z0": "3.2"})
        self.assertTrue(result["request_ok"])
        self.assertEqual({row["metric"] for row in normalize(result)}, {"ure200s0", "fu3010z0"})

    def test_all_missing_weather_is_a_failed_request_without_latest(self):
        result = self.fetch({"tre200s0": "-", "rre150z0": ""})
        self.assertFalse(result["request_ok"])
        self.assertEqual(normalize(result), [])
        self.assertFalse((self.root / "data" / self.source["id"] / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()
