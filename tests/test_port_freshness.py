"""A newly fetched page must not make an old gauge measurement current."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from risk_assessment.interfaces import RouteEvidence
from risk_assessment.local_data import _port_observation_time
from risk_assessment.observed import assess_observed_data, render_observed_summary


NOW = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)


class FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


class PortFreshnessTests(unittest.TestCase):
    def assess(self, observed_at, fetched_at=NOW):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "port_pegel_clean"
            folder.mkdir()
            reading = {"name": "Basel-Rheinhalle", "value": 800, "unit": "cm"}
            if observed_at is not None:
                reading["observed_at"] = observed_at
            (folder / "latest.json").write_text(json.dumps({
                "current_page_checked_at": fetched_at.isoformat(),
                "current_readings": [reading],
            }))
            with patch("risk_assessment.local_data.datetime", FrozenClock):
                return assess_observed_data(
                    root, RouteEvidence(alternate_route_available=True, alternate_route_suitable=True,
                                        estimated_arrival_at=NOW + timedelta(hours=2),
                                        alternate_arrival_at=NOW + timedelta(hours=1),
                                        material_needed_at=NOW + timedelta(hours=8)),
                    "basel_mittlere_bruecke_birsfelden",
                )

    def assert_excluded(self, result, status):
        self.assertEqual(result["current_observations"]["rhine"]["source_status"], status)
        component = next(item for item in result["manufacturing_priority_score"]["components"]
                         if item["name"] == "rhine")
        self.assertIsNone(component["contributed_points"])
        self.assertNotEqual(result["action"]["recommendation"], "reroute")
        self.assertNotIn(result["system_suggestion"]["suggestion"], ("Reroute", "Buffer", "Expedite"))

    def test_fresh_fetch_of_old_measurement_cannot_reroute(self):
        result = self.assess("01.01.2020 12:00")
        self.assert_excluded(result, "stale")
        rhine = result["current_observations"]["rhine"]
        self.assertEqual(rhine["port_snapshot_age_minutes"], 0)
        self.assertGreater(rhine["port_observation_age_minutes"], 30)

    def test_fresh_summer_local_measurement_can_reroute(self):
        result = self.assess("03.10.2026 13:50")
        rhine = result["current_observations"]["rhine"]
        self.assertEqual(rhine["port_observation_age_minutes"], 10)
        self.assertEqual(rhine["port_observed_at_utc"], "2026-10-03T11:50:00+00:00")
        self.assertEqual(result["action"]["recommendation"], "reroute")
        self.assertIn("measurement 10.0 min old", render_observed_summary(result))

    def test_missing_or_invalid_time_is_unknown(self):
        for value in (None, "", "not a date", 123, "2026-10-03T11:50:00"):
            with self.subTest(value=value):
                self.assert_excluded(self.assess(value), "unknown")

    def test_future_measurement_is_unknown_not_zero_age(self):
        self.assert_excluded(self.assess("2026-10-03T12:01:00Z"), "unknown")

    def test_freshness_boundary_uses_measurement(self):
        self.assertEqual(self.assess("2026-10-03T11:30:00Z")["action"]["recommendation"], "reroute")
        self.assert_excluded(self.assess("2026-10-03T11:29:59Z"), "stale")

    def test_winter_and_explicit_offsets_convert_to_utc(self):
        expected = datetime(2026, 1, 3, 12, tzinfo=timezone.utc)
        self.assertEqual(_port_observation_time("03.01.2026 13:00"), expected)
        self.assertEqual(_port_observation_time("2026-01-03T13:00:00+01:00"), expected)

    def test_ambiguous_and_nonexistent_wall_times_remain_unknown(self):
        for value in ("25.10.2026 02:30", "29.03.2026 02:30"):
            with self.subTest(value=value):
                self.assertIsNone(_port_observation_time(value))


if __name__ == "__main__":
    unittest.main()
