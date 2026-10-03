"""Route traffic findings must consider every explicitly selected counter."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from risk_assessment.disturbance import detect_traffic_disturbance
from risk_assessment.interfaces import RouteEvidence, TrafficCounterMatch
from risk_assessment.observed import assess_observed_data


class MultipleTrafficCounterTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.matches = tuple(TrafficCounterMatch(site, "north", 1) for site in ("A", "B"))

    def records(self, site, count, age_minutes=1):
        fields = {"sitecode": site, "directionname": "north", "lanecode": 1,
                  "weekday": self.now.weekday(), "hourfrom": self.now.hour}
        history = [{**fields, "datetimefrom": (self.now - timedelta(weeks=week)).isoformat(),
                    "total": value} for week, value in enumerate((90, 95, 100, 105, 110), 1)]
        return [*history, {**fields, "total": count,
                           "datetimefrom": (self.now - timedelta(minutes=age_minutes)).isoformat()}]

    def finding(self, records, matches=None):
        return detect_traffic_disturbance(
            Path("/unused"), self.matches if matches is None else matches,
            snapshot={"request_ok": True}, historical_records=records,
        )

    def test_newer_normal_counter_does_not_hide_route_anomaly(self):
        records = self.records("A", 1000, 2) + self.records("B", 100)
        expected = self.finding(records, self.matches[:1]).robust_z
        for order in (self.matches, tuple(reversed(self.matches))):
            with self.subTest(order=order):
                finding = self.finding(list(reversed(records)), order)
                self.assertEqual(finding.status, "detected")
                self.assertEqual(finding.robust_z, expected)
                self.assertIn("does not prove congestion", finding.action_effect)

    def test_missing_selected_counter_does_not_mean_clear_route(self):
        finding = self.finding(self.records("A", 100))
        self.assertEqual(finding.status, "unknown")
        self.assertIsNone(finding.robust_z)

    def test_stale_counter_does_not_mean_clear_route(self):
        finding = self.finding(self.records("A", 100) + self.records("B", 1000, 180))
        self.assertEqual(finding.status, "unknown")
        self.assertIsNone(finding.robust_z)

    def test_confirmed_anomaly_survives_missing_selected_counter(self):
        finding = self.finding(self.records("A", 1000))
        self.assertEqual(finding.status, "detected")
        self.assertGreater(finding.robust_z, 3)

    def test_normal_counters_combine_using_strongest_available_signal(self):
        records = self.records("A", 110, 2) + self.records("B", 100)
        expected = self.finding(records, self.matches[:1]).robust_z
        finding = self.finding(records)
        self.assertEqual(finding.status, "no_anomaly")
        self.assertEqual(finding.robust_z, expected)

    def test_combined_route_signal_reaches_observed_score_and_action(self):
        route = RouteEvidence(
            traffic_counters=self.matches, disruption_observed=False, exposed_handling=False,
            estimated_arrival_at=self.now + timedelta(hours=1),
            material_needed_at=self.now + timedelta(hours=8),
        )
        for count, include_second, expected_points, expected_action in (
            (1000, True, 10, "buffer"),
            (1000, False, 10, "buffer"),
            (100, False, None, "monitor"),
        ):
            with self.subTest(count=count, include_second=include_second):
                records = self.records("A", count, 2)
                if include_second:
                    records += self.records("B", 100)
                sources = {
                    "basel_dataset_100006": {"request_ok": True, "data": {"results": records},
                                             "history_results": records},
                    "opentransportdata_basel_region": {"request_ok": False, "data": {}},
                }
                result = assess_observed_data(Path("/unused"), route, source_snapshots=sources)
                component = result["manufacturing_priority_score"]["components"][1]
                self.assertEqual(component["contributed_points"], expected_points)
                self.assertEqual(result["action"]["recommendation"], expected_action)


if __name__ == "__main__":
    unittest.main()
