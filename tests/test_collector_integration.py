"""Verify collector snapshots and database rows use the risk engine's inputs."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pythontest"))

import api_requester
from normalize_observations import normalize
from weather_parameters import WEATHER_PARAMETERS

from risk_assessment.interfaces import RouteEvidence
from risk_assessment.local_data import collect_local_context
from risk_assessment.observed import assess_observed_data


class CollectorIntegrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.data_dir = self.root / "data"
        self.enterContext(patch.object(api_requester, "ROOT", self.root))
        self.enterContext(patch.object(api_requester, "DATA_DIR", self.data_dir))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.source = next(source for source in api_requester.SOURCES if source["kind"] == "meteo_current")

    def fetch_weather(self, observed_at):
        values = dict(zip(WEATHER_PARAMETERS, ("40", "0", "614", "10", "3.2", "7.1", "25", "73.4", "13.2")))
        body = ("Station/Location;Date;" + ";".join(values) +
                "\nBAS;" + observed_at.strftime("%Y%m%d%H%M") + ";" +
                ";".join(values.values()) + "\n").encode("cp1252")
        with patch.object(api_requester, "read_response", return_value=(200, {}, body, None)):
            return api_requester.check_meteoswiss_current(self.source)

    def test_same_nine_measurements_feed_database_rows_and_weather_score(self):
        fetched = self.fetch_weather(datetime.now(timezone.utc))
        rows = normalize(fetched)
        assessment = assess_observed_data(self.data_dir, RouteEvidence(exposed_handling=True))
        weather = assessment["current_observations"]["weather"]
        self.assertEqual(len(rows), 9)
        self.assertEqual(weather["source_status"], "observed")
        self.assertEqual(weather["measurements"], {row["metric"]: row["value"] for row in rows})
        self.assertEqual(assessment["current_observations"]["weather_score_details"]["score"], 100)
        component = next(item for item in assessment["manufacturing_priority_score"]["components"] if item["name"] == "weather")
        self.assertEqual(component["contributed_points"], 40)
        self.assertEqual(assessment["action"]["recommendation"], "monitor")

    def test_network_failure_preserves_weather_without_new_database_observations(self):
        self.fetch_weather(datetime.now(timezone.utc))
        latest = self.data_dir / self.source["id"] / "latest.json"
        previous = latest.read_bytes()
        with patch.object(api_requester, "read_response", return_value=(None, {}, None, "network unavailable")):
            failed = api_requester.check_meteoswiss_current(self.source)
        self.assertEqual(normalize(failed), [])
        self.assertEqual(latest.read_bytes(), previous)
        self.assertTrue((latest.parent / "last_error.json").exists())
        self.assertEqual(len((latest.parent / "history.jsonl").read_text().splitlines()), 2)
        self.assertEqual(collect_local_context(self.data_dir)["weather"]["source_status"], "observed")

    def test_fresh_fetch_does_not_make_old_weather_current(self):
        self.fetch_weather(datetime.now(timezone.utc) - timedelta(hours=4))
        assessment = assess_observed_data(self.data_dir, RouteEvidence(exposed_handling=True))
        self.assertEqual(assessment["current_observations"]["weather"]["source_status"], "stale")
        component = next(item for item in assessment["manufacturing_priority_score"]["components"] if item["name"] == "weather")
        self.assertIsNone(component["contributed_points"])

    def test_legacy_failed_traffic_and_rhine_snapshots_remain_unknown(self):
        for source in ("basel_dataset_100006", "basel_dataset_100089"):
            folder = self.data_dir / source
            folder.mkdir(parents=True)
            (folder / "latest.json").write_text(json.dumps({"request_ok": False, "data": None}))
        context = collect_local_context(self.data_dir)
        self.assertEqual(context["traffic"]["source_status"], "unknown")
        self.assertIsNone(context["rhine"]["basel_stadt_latest"])


if __name__ == "__main__":
    unittest.main()
