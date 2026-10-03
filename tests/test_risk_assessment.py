import unittest
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from risk_assessment.decision import decide_action
from risk_assessment.disturbance import detect_traffic_disturbance
from risk_assessment.interfaces import ExposureMetrics, RouteEvidence, TemperatureReading
from risk_assessment.logistics import classify_rhine_high_water, traffic_volume_anomaly
from risk_assessment.thermal import analyze_temperature_series, simulate_package_temperature, time_to_temperature_limit


class ThermalTests(unittest.TestCase):
    def test_linear_crossing_integrates_only_exposed_triangle(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = analyze_temperature_series([
            TemperatureReading(start, 7, 0),
            TemperatureReading(start + timedelta(minutes=10), 9, 0),
        ])
        self.assertAlmostEqual(result.minutes_above_max, 5)
        self.assertAlmostEqual(result.hot_degree_hours, 2.5 / 60)
        self.assertAlmostEqual(result.peak_above_max_c, 1)

    def test_long_sensor_gap_is_unknown_not_interpolated(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = analyze_temperature_series([
            TemperatureReading(start, 9, 0),
            TemperatureReading(start + timedelta(minutes=20), 9, 0),
        ])
        self.assertEqual(result.minutes_above_max, 0)
        self.assertTrue(result.incomplete_history)
        self.assertTrue(result.quality_review_required)

    def test_uncertainty_touching_boundary_requires_review(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = analyze_temperature_series([TemperatureReading(start, 7.5, 0.5)])
        self.assertEqual(result.borderline_readings, 1)
        self.assertTrue(result.quality_review_required)

    def test_exact_boundary_is_in_range_but_missing_accuracy_requires_review(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        exact = analyze_temperature_series([TemperatureReading(start, 8, 0)])
        self.assertFalse(exact.quality_review_required)
        unknown_accuracy = analyze_temperature_series([TemperatureReading(start, 5)])
        self.assertTrue(unknown_accuracy.sensor_accuracy_unknown)
        self.assertTrue(unknown_accuracy.quality_review_required)

    def test_scenario_is_repeatable_curve_and_not_sensor_data(self):
        curve = simulate_package_temperature(7, 40, timedelta(minutes=30), timedelta(minutes=90))
        self.assertEqual(len(curve), 31)
        self.assertAlmostEqual(curve[-1].temperature_c, 40 + (7 - 40) * __import__("math").exp(-1 / 3))

    def test_limit_time(self):
        minutes = time_to_temperature_limit(7, 40, 8, timedelta(minutes=90))
        self.assertAlmostEqual(minutes, 90 * __import__("math").log(33 / 32))
        self.assertIsNone(time_to_temperature_limit(7, 5, 8, timedelta(minutes=90)))


class DecisionTests(unittest.TestCase):
    def test_quality_review_precedes_reroute(self):
        thermal = ExposureMetrics(0, 0, 0, 0, 0, 0, quality_review_required=True)
        route = RouteEvidence(route_restricted=True, alternate_route_available=True)
        self.assertEqual(decide_action(thermal, route).action, "quality_review")

    def test_restriction_with_alternate_route_reroutes(self):
        thermal = ExposureMetrics(0, 0, 0, 0, 0, 0)
        route = RouteEvidence(route_restricted=True, alternate_route_available=True)
        self.assertEqual(decide_action(thermal, route).action, "reroute")

    def test_missing_telemetry_requires_review(self):
        self.assertEqual(decide_action(None, RouteEvidence()).action, "quality_review")


class LogisticsTests(unittest.TestCase):
    def test_ten_record_feed_is_not_a_traffic_baseline(self):
        result = traffic_volume_anomaly(100, [90, 95, 100])
        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.robust_z)

    def test_traffic_mad_anomaly_does_not_claim_delay(self):
        result = traffic_volume_anomaly(200, [90, 95, 100, 105, 110])
        self.assertEqual(result.status, "available")
        self.assertGreater(result.robust_z, 0)
        self.assertIn("not proof", result.reason)

    def test_rhine_threshold_requires_segment(self):
        self.assertEqual(classify_rhine_high_water(800, None).status, "unknown")
        self.assertEqual(classify_rhine_high_water(800, "basel_mittlere_bruecke_birsfelden").status, "restricted")
        self.assertEqual(classify_rhine_high_water(800, "rheinfelden_kembs").status, "pre_alert")

    def test_fresh_route_matched_traffic_spike_is_detected_but_not_a_delay(self):
        now = datetime.now(timezone.utc)
        baseline = [90, 95, 100, 105, 110]
        records = []
        for weeks_back, count in enumerate(baseline, start=1):
            stamp = now - timedelta(days=7 * weeks_back)
            records.append({"sitecode": "counter-1", "datetimefrom": stamp.isoformat(), "directionname": "north",
                            "lanecode": 1, "weekday": now.weekday(), "hourfrom": now.hour, "total": count})
        records.append({"sitecode": "counter-1", "datetimefrom": now.isoformat(), "directionname": "north",
                        "lanecode": 1, "weekday": now.weekday(), "hourfrom": now.hour, "total": 200})
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "basel_dataset_100006"
            directory.mkdir()
            snapshot = {"request_ok": True, "data": {"results": records}}
            (directory / "latest.json").write_text(json.dumps(snapshot), encoding="utf-8")
            finding = detect_traffic_disturbance(Path(temporary))
        self.assertEqual(finding.status, "detected")
        self.assertIn("does not prove congestion", finding.action_effect)


if __name__ == "__main__":
    unittest.main()
