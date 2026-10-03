"""Quality holds override score, deadline, and alternate-route recommendations."""

import unittest
from datetime import datetime, timedelta, timezone

from risk_assessment.decision import decide_action, suggest_system_action
from risk_assessment.interfaces import ExposureMetrics, RouteEvidence, TemperatureReading
from risk_assessment.priority import calculate_priority_score
from risk_assessment.thermal import analyze_temperature_series


class QualityHoldTests(unittest.TestCase):
    def test_measured_excursion_cannot_expedite_with_plenty_of_slack(self):
        now = datetime.now(timezone.utc)
        thermal = analyze_temperature_series([
            TemperatureReading(now, 10, 0),
            TemperatureReading(now + timedelta(minutes=15), 10, 0),
        ])
        route = RouteEvidence(
            disruption_observed=False,
            estimated_arrival_at=now + timedelta(hours=1),
            material_needed_at=now + timedelta(hours=20),
        )
        score = calculate_priority_score(thermal, route)
        self.assertEqual(score.minimum, 50)
        self.assertEqual(decide_action(thermal, route).action, "quality_review")
        suggestion = suggest_system_action(thermal, route, score)
        self.assertEqual(suggestion["suggestion"], "Quality review")
        self.assertIn("until authorized release", suggestion["reason"])

    def test_hold_blocks_route_and_deadline_triggers_for_all_review_causes(self):
        now = datetime.now(timezone.utc)
        route = RouteEvidence(
            disruption_observed=True, route_restricted=True,
            alternate_route_available=True,
            estimated_arrival_at=now + timedelta(hours=2),
            material_needed_at=now + timedelta(hours=1),
        )
        cases = [None]
        for cause in ("excursion", "borderline", "incomplete", "accuracy_unknown"):
            cases.append(ExposureMetrics(
                0, 0, 0, 0, 0.5 if cause == "excursion" else 0, 0,
                borderline_readings=int(cause == "borderline"),
                incomplete_history=cause == "incomplete",
                sensor_accuracy_unknown=cause == "accuracy_unknown",
                quality_review_required=True,
            ))
        for thermal in cases:
            with self.subTest(thermal=thermal):
                assessment = decide_action(thermal, route)
                suggestion = suggest_system_action(
                    thermal, route, calculate_priority_score(thermal, route),
                )
                self.assertEqual(assessment.action, "quality_review")
                self.assertEqual(suggestion["suggestion"], "Quality review")
                self.assertEqual(assessment.reason, suggestion["reason"])
                self.assertIn("production use remain blocked", suggestion["reason"])

    def test_clear_temperature_evidence_preserves_logistics_actions(self):
        now = datetime.now(timezone.utc)
        thermal = ExposureMetrics(0, 0, 0, 0, 0, 0)
        routes = [
            (RouteEvidence(route_restricted=True, alternate_route_available=True), "Reroute"),
            (RouteEvidence(disruption_observed=False, estimated_arrival_at=now,
                           material_needed_at=now), "Expedite"),
            (RouteEvidence(disruption_observed=True), "Buffer"),
        ]
        for route, expected in routes:
            with self.subTest(expected=expected):
                suggestion = suggest_system_action(
                    thermal, route, calculate_priority_score(thermal, route),
                )
                self.assertEqual(suggestion["suggestion"], expected)


if __name__ == "__main__":
    unittest.main()
