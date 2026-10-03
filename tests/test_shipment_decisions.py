"""Shipment context gates one shared operator decision policy."""

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from risk_assessment.cli import build_parser, parse_traffic_counters, run_demo_suite_data
from risk_assessment.decision import decide_action, suggest_system_action
from risk_assessment.disturbance import detect_traffic_disturbance
from risk_assessment.interfaces import ExposureMetrics, RouteEvidence, TrafficCounterMatch
from risk_assessment.observed import assess_observed_data
from risk_assessment.priority import calculate_priority_score


class ShipmentDecisionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.thermal = ExposureMetrics(0, 0, 0, 0, 0, 0)
        self.route = RouteEvidence(
            disruption_observed=False, exposed_handling=False,
            estimated_arrival_at=self.now + timedelta(hours=1),
            material_needed_at=self.now + timedelta(hours=8),
        )

    def test_missing_eta_handling_or_route_status_is_monitor(self):
        for route in (replace(self.route, estimated_arrival_at=None),
                      replace(self.route, material_needed_at=None),
                      replace(self.route, exposed_handling=None),
                      replace(self.route, disruption_observed=None)):
            with self.subTest(route=route):
                self.assertEqual(decide_action(self.thermal, route).action, "monitor")

    def test_observed_empty_and_hot_weather_have_consistent_monitor_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for hot_weather in (False, True):
                if hot_weather:
                    folder = root / "meteoswiss_basel_temperature"
                    folder.mkdir()
                    (folder / "latest.json").write_text(json.dumps({
                        "request_ok": True, "checked_at": self.now.isoformat(),
                        "data": {"station": {"observed_at_utc": self.now.isoformat(),
                                 "measurements": {"tre200s0": 40, "rre150z0": 0, "fu3010z1": 0}}},
                    }))
                result = assess_observed_data(root)
                self.assertEqual(result["action"]["recommendation"], "monitor")
                self.assertEqual(result["system_suggestion"]["suggestion"], "Monitor")
                self.assertEqual(result["action"]["reason"], result["system_suggestion"]["reason"])
                weather = result["manufacturing_priority_score"]["components"][0]
                self.assertIsNone(weather["contributed_points"])
            exposed = assess_observed_data(root, replace(self.route, exposed_handling=True))
            self.assertEqual(exposed["manufacturing_priority_score"]["components"][0]["contributed_points"], 40)
            self.assertEqual(exposed["action"]["recommendation"], "buffer")

    def test_weather_requires_exposed_handling_for_action(self):
        protected = replace(self.route, weather_severity=100)
        self.assertEqual(decide_action(self.thermal, protected).action, "normal")
        self.assertEqual(decide_action(self.thermal, replace(protected, exposed_handling=True)).action, "buffer")

    def test_urgent_deadline_does_not_override_unknown_handling_or_route(self):
        urgent = replace(self.route, material_needed_at=self.now)
        for route in (replace(urgent, exposed_handling=None),
                      replace(urgent, disruption_observed=None),
                      replace(urgent, exposed_handling=True, weather_severity=None)):
            with self.subTest(route=route):
                self.assertEqual(decide_action(self.thermal, route).action, "monitor")

    def test_traffic_anomaly_requires_route_match_for_score_and_action(self):
        unmatched = replace(self.route, traffic_anomaly=10)
        self.assertEqual(decide_action(self.thermal, unmatched).action, "normal")
        self.assertEqual(calculate_priority_score(self.thermal, unmatched).components["route"], 0)
        matched = replace(unmatched, traffic_route_matched=True)
        self.assertEqual(decide_action(self.thermal, matched).action, "buffer")
        self.assertEqual(calculate_priority_score(self.thermal, matched).components["route"], 100)

    def test_alternate_requires_suitability_earlier_arrival_and_deadline(self):
        restricted = replace(self.route, route_restricted=True, alternate_route_available=True)
        for route in (restricted, replace(restricted, alternate_route_suitable=True),
                      replace(restricted, alternate_route_suitable=True,
                              alternate_arrival_at=self.now + timedelta(hours=2))):
            with self.subTest(route=route):
                self.assertEqual(decide_action(self.thermal, route).action, "monitor")
        verified = replace(restricted, alternate_route_suitable=True,
                           alternate_arrival_at=self.now + timedelta(minutes=30))
        self.assertEqual(decide_action(self.thermal, verified).action, "reroute")
        late = replace(verified, estimated_arrival_at=self.now + timedelta(hours=10),
                       alternate_arrival_at=self.now + timedelta(hours=9))
        self.assertEqual(decide_action(self.thermal, late).action, "monitor")

    def test_each_output_uses_same_action_and_reason(self):
        for route in (self.route, replace(self.route, disruption_observed=True),
                      replace(self.route, material_needed_at=self.now), RouteEvidence()):
            assessment = decide_action(self.thermal, route)
            suggestion = suggest_system_action(self.thermal, route, calculate_priority_score(self.thermal, route))
            self.assertEqual(suggestion["suggestion"].lower(), assessment.action)
            self.assertEqual(suggestion["reason"], assessment.reason)

    def test_counter_filter_ignores_newer_spike_elsewhere(self):
        baseline = [90, 95, 100, 105, 110]
        records = [{"sitecode": "route-site", "directionname": "north", "lanecode": 1,
                    "weekday": self.now.weekday(), "hourfrom": self.now.hour, "total": count,
                    "datetimefrom": (self.now - timedelta(weeks=i)).isoformat()}
                   for i, count in enumerate(baseline, 1)]
        records += [{**records[0], "datetimefrom": (self.now - timedelta(minutes=1)).isoformat(), "total": 100},
                    {**records[0], "sitecode": "elsewhere", "datetimefrom": self.now.isoformat(), "total": 10000}]
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "basel_dataset_100006"
            folder.mkdir()
            (folder / "latest.json").write_text(json.dumps({"request_ok": True, "data": {"results": records}}))
            finding = detect_traffic_disturbance(Path(temporary), (TrafficCounterMatch("route-site", "north", 1),))
            self.assertEqual(finding.status, "no_anomaly")
            self.assertEqual(detect_traffic_disturbance(Path(temporary)).status, "unknown")

    def test_cli_route_contract_and_demo_paths(self):
        self.assertEqual(parse_traffic_counters(["route-site|north|1"]), (TrafficCounterMatch("route-site", "north", 1),))
        with self.assertRaises(ValueError):
            parse_traffic_counters(["route-site"])
        with tempfile.TemporaryDirectory() as temporary:
            args = build_parser().parse_args(["--scenario", "all", "--data-dir", temporary,
                                              "--weather-source", "local"])
            result = run_demo_suite_data(args)
            self.assertEqual([case["assessment"]["action"] for case in result["scenarios"][:4]],
                             ["normal", "buffer", "expedite", "reroute"])
            for case in result["scenarios"]:
                self.assertEqual(case["assessment"]["reason"], case["system_suggestion"]["reason"])


if __name__ == "__main__":
    unittest.main()
