"""Road evidence calculations and exclusions, using synthetic shipment mappings."""

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from risk_assessment.cli import build_parser, run_observed
from risk_assessment.disturbance import Disturbance
from risk_assessment.interfaces import RoadCounterMatch, RoadEventMatch, RouteEvidence, TrafficCounterMatch
from risk_assessment.observed import assess_observed_data
from risk_assessment.road_traffic import assess_road_traffic


class RoadTrafficTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.now = datetime.now(timezone.utc)
        self.timestamp = (self.now - timedelta(minutes=1)).isoformat()
        self.reading = {"site_id": "detector", "observed_at": self.timestamp, "values": [
            {"index": "12", "fields": {"speed": "40"}},
            {"index": "11", "fields": {"vehicleFlowRate": "600"}},
        ]}
        self.event = {"id": "incident", "updated_at": self.timestamp,
                      "validity_status": "definedByValidityTimeSpec", "valid_from": self.timestamp,
                      "valid_until": None, "descriptions": ["Freigegeben: road restriction"]}
        self.payload = {"request_ok": True, "data": {"fetched_at": self.timestamp, "errors": [],
                        "traffic_counters": {"sites": [], "current_readings": [self.reading]},
                        "traffic_situations": [self.event]}}
        self.folder = self.root / "opentransportdata_basel_region"
        self.folder.mkdir()
        self.route = RouteEvidence(road_counters=(RoadCounterMatch("detector", "light", 80),))

    def save(self):
        (self.folder / "latest.json").write_text(json.dumps(self.payload))

    def assess(self, route=None):
        self.save()
        return assess_road_traffic(self.root, route or self.route, evaluated_at=self.now)

    def event_route(self):
        return RouteEvidence(road_events=(RoadEventMatch("incident", "restricted", self.timestamp),))

    def test_minute_watch_snapshot_supersedes_regular_collector(self):
        import copy
        self.save()
        standalone = copy.deepcopy(self.payload["data"])
        standalone["fetched_at"] = self.now.isoformat()
        standalone["traffic_counters"]["current_readings"][0]["values"][0]["fields"]["speed"] = "20"
        folder = self.root / "opentransportdata"
        folder.mkdir()
        (folder / "latest.json").write_text(json.dumps(standalone))
        self.assertEqual(assess_road_traffic(self.root, self.route, evaluated_at=self.now).severity, 75)

    def test_speed_loss_and_zero_at_or_above_reference(self):
        self.assertEqual(self.assess().severity, 50)
        for speed in (80, 90):
            self.reading["values"][0]["fields"]["speed"] = speed
            self.assertEqual(self.assess().severity, 0)

    def test_zero_or_missing_flow_never_means_closure(self):
        for flow in (0, None, "NaN", -1):
            self.reading["values"][1]["fields"]["vehicleFlowRate"] = flow
            result = self.assess()
            self.assertIsNone(result.severity)
            self.assertFalse(result.restricted)

    def test_invalid_speed_and_missing_vehicle_class(self):
        for speed in (-1, "NaN", "Infinity", None):
            self.reading["values"][0]["fields"]["speed"] = speed
            self.assertIsNone(self.assess().severity)
        self.assertIsNone(self.assess(replace(self.route, road_counters=(RoadCounterMatch("detector", "heavy", 80),))).severity)

    def test_stale_future_and_naive_measurement_not_refreshed_by_fetch(self):
        for stamp in ((self.now - timedelta(minutes=6)).isoformat(),
                      (self.now + timedelta(minutes=1)).isoformat(), "2026-10-03T12:00:00"):
            self.reading["observed_at"] = stamp
            self.assertIsNone(self.assess().severity)

    def test_unmatched_data_visible_without_scoring(self):
        result = self.assess(RouteEvidence())
        self.assertIsNone(result.severity)
        self.assertEqual(len(result.context["current_readings"]), 1)

    def test_unknown_reference_rejected(self):
        for speed in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.assess(replace(self.route, road_counters=(RoadCounterMatch("detector", "light", speed),)))

    def test_verified_current_event_sets_restriction(self):
        result = self.assess(self.event_route())
        self.assertEqual(result.severity, 100)
        self.assertTrue(result.restricted)

    def test_revoked_in_supported_languages_is_excluded(self):
        for prefix in ("Aufgehoben:", "Révoqué:", "Revocato:", "Revoked:"):
            self.event["descriptions"] = [prefix + " road restriction"]
            result = self.assess(self.event_route())
            self.assertIsNone(result.severity)
            self.assertFalse(result.restricted)

    def test_changed_or_legacy_event_needs_new_verification(self):
        for timestamp in (None, self.now.isoformat()):
            self.event["updated_at"] = timestamp
            self.assertIsNone(self.assess(self.event_route()).severity)

    def test_event_validity_and_fetch_age(self):
        changes = [("valid_from", (self.now + timedelta(hours=1)).isoformat()),
                   ("valid_until", self.timestamp), ("valid_until", "bad"),
                   ("validity_status", "suspended"), ("complex_validity", True)]
        for key, value in changes:
            original = self.event.get(key)
            self.event[key] = value
            self.assertIsNone(self.assess(self.event_route()).severity)
            self.event[key] = original
        self.payload["data"]["fetched_at"] = (self.now - timedelta(minutes=16)).isoformat()
        self.assertIsNone(self.assess(self.event_route()).severity)

    def test_partial_fetch_keeps_independent_valid_counters(self):
        self.payload["request_ok"] = False
        self.payload["data"]["errors"] = ["Traffic Situations: unavailable"]
        self.assertEqual(self.assess().severity, 50)
        self.assertIsNone(self.assess(self.event_route()).severity)
        self.payload["data"]["errors"] = ["Traffic Counters: unavailable"]
        self.assertIsNone(self.assess().severity)

    def test_missing_selected_counter_keeps_partial_score_unknown(self):
        route = replace(self.route, road_counters=(*self.route.road_counters, RoadCounterMatch("missing", "light", 80)))
        self.assertIsNone(self.assess(route).severity)

    def test_same_incident_and_speed_not_added_twice(self):
        route = replace(self.route, road_events=self.event_route().road_events)
        self.assertEqual(self.assess(route).severity, 100)
        self.save()
        result = assess_observed_data(self.root, route)
        traffic = next(item for item in result["manufacturing_priority_score"]["components"] if item["name"] == "traffic")
        self.assertEqual(traffic["contributed_points"], 10)
        self.assertEqual(result["action"]["recommendation"], "monitor")
        self.assertIn("restricted", result["action"]["reason"])

    def test_cli_and_missing_evidence_bounds(self):
        self.save()
        args = build_parser().parse_args(["--data-dir", str(self.root), "--weather-source", "local",
                                          "--road-counter", "detector|light|80"])
        result = run_observed(args)
        score = result["manufacturing_priority_score"]
        self.assertEqual(score["score"], 5)
        self.assertEqual((score["minimum"], score["maximum"]), (5, 95))
        self.assertEqual(score["evidence_coverage"]["available"], 1)
        self.assertEqual(result["system_suggestion"]["suggestion"], "Monitor")

    def test_speed_watch_uses_existing_slack_policy(self):
        self.save()
        route = replace(self.route, exposed_handling=False,
                        estimated_arrival_at=self.now + timedelta(hours=1),
                        material_needed_at=self.now + timedelta(hours=8))
        self.assertEqual(assess_observed_data(self.root, route)["action"]["recommendation"], "buffer")
        route = replace(route, material_needed_at=self.now + timedelta(hours=2))
        self.assertEqual(assess_observed_data(self.root, route)["action"]["recommendation"], "expedite")

    def test_available_road_speed_does_not_hide_selected_missing_count_baseline(self):
        self.save()
        route = replace(self.route, traffic_counters=(TrafficCounterMatch("site", "North", 1),))
        result = assess_observed_data(self.root, route)
        traffic = next(item for item in result["manufacturing_priority_score"]["components"] if item["name"] == "traffic")
        self.assertIsNone(traffic["contributed_points"])
        self.assertEqual(result["manufacturing_priority_score"]["evidence_coverage"]["available"], 0)
        self.assertEqual(result["manufacturing_priority_score"]["maximum"], 100)

    def test_normal_count_does_not_hide_selected_missing_road_counter(self):
        self.save()
        route = replace(self.route, road_counters=(RoadCounterMatch("missing", "light", 80),),
                        traffic_counters=(TrafficCounterMatch("site", "North", 1),))
        finding = Disturbance("traffic", "no_anomaly", "Comparable count is normal", (), "none", robust_z=0)
        with patch("risk_assessment.observed.detect_traffic_disturbance", return_value=finding):
            result = assess_observed_data(self.root, route)
        traffic = next(item for item in result["manufacturing_priority_score"]["components"] if item["name"] == "traffic")
        self.assertIsNone(traffic["contributed_points"])
        self.assertEqual(result["manufacturing_priority_score"]["maximum"], 100)

    def test_known_maximum_still_saturates_despite_missing_selected_count(self):
        self.save()
        route = replace(self.event_route(), traffic_counters=(TrafficCounterMatch("site", "North", 1),))
        result = assess_observed_data(self.root, route)
        traffic = next(item for item in result["manufacturing_priority_score"]["components"] if item["name"] == "traffic")
        self.assertEqual(traffic["contributed_points"], 10)


if __name__ == "__main__":
    unittest.main()
