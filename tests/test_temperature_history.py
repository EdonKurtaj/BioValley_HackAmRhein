"""Temperature history must cover the requested period and remain current."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from risk_assessment.decision import decide_action, suggest_system_action
from risk_assessment.interfaces import RouteEvidence, TemperatureReading
from risk_assessment.priority import calculate_priority_score
from risk_assessment.thermal import analyze_temperature_series


class TemperatureHistoryTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        self.end = self.start + timedelta(minutes=30)

    def reading(self, at):
        return TemperatureReading(at, 5, 0)

    def analyze(self, readings, **kwargs):
        return analyze_temperature_series(
            readings, monitoring_started_at=self.start,
            evaluated_at=kwargs.pop("evaluated_at", self.end), **kwargs,
        )

    def assert_hold(self, result):
        self.assertTrue(result.incomplete_history)
        self.assertTrue(result.quality_review_required)
        route = RouteEvidence(disruption_observed=False)
        score = calculate_priority_score(result, route)
        self.assertIsNone(score.components["thermal"])
        self.assertEqual(decide_action(result, route).action, "quality_review")
        self.assertEqual(suggest_system_action(result, route, score)["suggestion"], "Quality review")

    def test_old_single_reading_cannot_produce_normal(self):
        result = self.analyze([self.reading(self.start)],
                              evaluated_at=self.start + timedelta(days=30))
        self.assert_hold(result)
        self.assertTrue(any("single" in text for text in result.evidence))
        self.assertTrue(any("too old" in text for text in result.evidence))

    def test_even_fresh_single_reading_requires_review(self):
        self.assert_hold(self.analyze([self.reading(self.end)]))

    def test_missing_monitoring_start_requires_review(self):
        result = analyze_temperature_series(
            [self.reading(self.start), self.reading(self.start + timedelta(minutes=15))],
            evaluated_at=self.start + timedelta(minutes=15),
        )
        self.assert_hold(result)
        self.assertTrue(any("start is unknown" in text for text in result.evidence))

    def test_missing_start_of_transport_requires_review(self):
        result = self.analyze([self.reading(self.start + timedelta(minutes=15)), self.reading(self.end)])
        self.assert_hold(result)
        self.assertTrue(any("beginning" in text for text in result.evidence))

    def test_stale_last_reading_requires_review_without_internal_gaps(self):
        result = self.analyze([self.reading(self.start), self.reading(self.start + timedelta(minutes=10))])
        self.assert_hold(result)
        self.assertEqual(result.hot_degree_hours, 0)
        self.assertTrue(any("too old" in text for text in result.evidence))

    def test_complete_history_is_usable_at_explicit_replay_time(self):
        result = self.analyze([
            self.reading(self.start), self.reading(self.start + timedelta(minutes=15)),
            self.reading(self.end),
        ])
        self.assertFalse(result.incomplete_history)
        self.assertFalse(result.quality_review_required)

    def test_freshness_boundary_and_configured_tolerance(self):
        readings = [self.reading(self.start), self.reading(self.start + timedelta(minutes=15))]
        self.assertFalse(self.analyze(readings).incomplete_history)
        self.assert_hold(self.analyze(readings, evaluated_at=self.end + timedelta(seconds=1)))
        self.assert_hold(self.analyze(readings, max_gap=timedelta(minutes=10)))

    def test_default_evaluation_uses_wall_clock_not_last_reading(self):
        with patch("risk_assessment.thermal.datetime") as clock:
            clock.now.return_value = self.end + timedelta(days=30)
            result = analyze_temperature_series(
                [self.reading(self.start), self.reading(self.start + timedelta(minutes=15))],
                monitoring_started_at=self.start,
            )
        self.assert_hold(result)

    def test_invalid_time_boundaries_are_rejected(self):
        with self.assertRaises(ValueError):
            self.analyze([self.reading(self.end + timedelta(seconds=1))])
        with self.assertRaises(ValueError):
            self.analyze([self.reading(self.start - timedelta(seconds=1))])
        with self.assertRaises(ValueError):
            self.analyze([], evaluated_at=self.start)
        with self.assertRaises(ValueError):
            self.analyze([], evaluated_at=self.end.replace(tzinfo=None))


if __name__ == "__main__":
    unittest.main()
