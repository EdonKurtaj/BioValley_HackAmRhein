import unittest
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from risk_assessment.decision import decide_action
from risk_assessment.disturbance import detect_traffic_disturbance, score_weather_context
from risk_assessment.interfaces import ExposureMetrics, RouteEvidence, TemperatureReading
from risk_assessment.logistics import classify_rhine_high_water, traffic_volume_anomaly
from risk_assessment.observed import assess_observed_data
from risk_assessment.priority import calculate_priority_score
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


class PriorityScoreTests(unittest.TestCase):
    def test_all_high_signals_add_to_100_points_without_becoming_damage_probability(self):
        thermal = ExposureMetrics(60, 0, 2, 0, 0.5, 0)
        now = datetime.now(timezone.utc)
        route = RouteEvidence(disruption_observed=True, estimated_arrival_at=now,
                              material_needed_at=now, buffer_hours=4)
        score = calculate_priority_score(thermal, route)
        self.assertEqual(score.minimum, 100)
        self.assertEqual(score.maximum, 100)
        self.assertEqual(score.coverage_percent, 100)
        self.assertEqual(score.weighted_points, {"thermal": 40.0, "route": 35.0, "urgency": 25.0})
        self.assertIn("not a probability", score.interpretation)

    def test_missing_inputs_expand_range_instead_of_counting_as_zero(self):
        thermal = ExposureMetrics(0, 0, 0, 0, 0.25, 0)
        score = calculate_priority_score(thermal, RouteEvidence())
        self.assertEqual(score.minimum, 20)
        self.assertEqual(score.maximum, 80)
        self.assertAlmostEqual(score.coverage_percent, 100 / 3)
        self.assertEqual(score.score_weight_coverage_percent, 50)
        self.assertIsNone(score.components["route"])
        self.assertIsNone(score.components["urgency"])

    def test_incomplete_temperature_history_is_unknown_for_scoring(self):
        thermal = ExposureMetrics(0, 0, 0, 0, 0, 0, incomplete_history=True)
        score = calculate_priority_score(thermal, RouteEvidence())
        self.assertEqual(score.minimum, 0)
        self.assertEqual(score.maximum, 100)
        self.assertEqual(score.coverage_percent, 0)
        self.assertIsNone(score.components["thermal"])

    def test_traffic_anomaly_scales_to_watch_threshold(self):
        route = RouteEvidence(traffic_anomaly=1.5)
        score = calculate_priority_score(None, route)
        self.assertEqual(score.components["route"], 50)
        self.assertEqual(score.minimum, 17.5)

    def test_hot_and_cold_degree_hours_both_add_to_thermal_component(self):
        thermal = ExposureMetrics(0, 0, 0, 0, 0.25, 0.25)
        score = calculate_priority_score(thermal, RouteEvidence())
        self.assertEqual(score.components["thermal"], 100)
        self.assertEqual(score.weighted_points["thermal"], 40)


class ObservedDataScoreTests(unittest.TestCase):
    def test_normal_weather_does_not_create_a_package_excursion_score(self):
        result = score_weather_context({"tre200s0": 18.4, "rre150z0": 0, "fu3010z1": 7.2})
        self.assertEqual(result["status"], "no_anomaly")
        self.assertEqual(result["score"], 0)

    def test_weather_context_caps_weather_contribution_at_its_weight(self):
        result = score_weather_context({"tre200s0": 35, "rre150z0": 0, "fu3010z1": 7.2})
        self.assertEqual(result["score"], 50)

    def test_observed_assessment_excludes_stale_or_unmatched_inputs(self):
        now = datetime.now(timezone.utc)
        stamp = now.isoformat()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather_dir = root / "meteoswiss_basel_temperature"
            traffic_dir = root / "basel_dataset_100006"
            port_dir = root / "port_pegel_clean"
            for directory in (weather_dir, traffic_dir, port_dir):
                directory.mkdir()
            (weather_dir / "latest.json").write_text(json.dumps({
                "request_ok": True, "checked_at": stamp,
                "data": {"station": {"observed_at_utc": stamp, "observed_at": stamp,
                         "age_minutes_at_fetch": 0, "station_id": "BAS",
                         "measurements": {"tre200s0": 18.4, "rre150z0": 0, "fu3010z1": 7.2}}},
            }), encoding="utf-8")
            row = {"datetimefrom": stamp, "datetimeto": stamp, "sitecode": "counter",
                   "directionname": "north", "lanecode": 1, "weekday": now.weekday(),
                   "hourfrom": now.hour, "total": 66, "sitename": "Example counter"}
            (traffic_dir / "latest.json").write_text(json.dumps({
                "request_ok": True, "checked_at": stamp, "data": {"results": [row]},
            }), encoding="utf-8")
            (port_dir / "latest.json").write_text(json.dumps({
                "current_page_checked_at": stamp,
                "current_readings": [{"name": "Basel-Rheinhalle", "value": 479, "unit": "cm"}],
                "flood_thresholds": [{"mark": "I", "water_level": 700}],
            }), encoding="utf-8")
            result = assess_observed_data(root)

        score = result["manufacturing_priority_score"]
        self.assertEqual(score["score"], 0)
        self.assertEqual(score["coverage_percent"], 25)
        self.assertEqual(score["score_weight_coverage_percent"], 40)
        self.assertEqual([item["contributed_points"] for item in score["components"]], [0, None, None, None])
        self.assertIn("no package-temperature curve", result["mode"])

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            weather_dir = root / "meteoswiss_basel_temperature"
            weather_dir.mkdir()
            old_observation = (now - timedelta(hours=1)).isoformat()
            (weather_dir / "latest.json").write_text(json.dumps({
                "request_ok": True, "checked_at": stamp,
                "data": {"station": {"observed_at_utc": old_observation, "age_minutes_at_fetch": 0,
                         "measurements": {"tre200s0": 18.4, "rre150z0": 0, "fu3010z1": 7.2}}},
            }), encoding="utf-8")
            result = assess_observed_data(root)
            self.assertEqual(result["current_observations"]["weather"]["source_status"], "stale")
            self.assertEqual(result["manufacturing_priority_score"]["score"], None)


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
