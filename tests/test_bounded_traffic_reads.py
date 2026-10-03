"""Live traffic reads stay bounded while selected-counter baselines remain usable."""

from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from risk_assessment.cli import _supabase_sources_for, build_parser
from risk_assessment.disturbance import detect_traffic_disturbance
from risk_assessment.interfaces import TrafficCounterMatch
from risk_assessment.supabase_data import (
    TRAFFIC_BASELINE_LIMIT, TRAFFIC_CONTEXT_LIMIT, _observations, fetch_supabase_sources,
)


class BoundedTrafficReadTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.counter = TrafficCounterMatch("route-site", "north", 1)
        self.rows = [self.row("elsewhere", self.now - timedelta(seconds=index), 100)
                     for index in range(1500)]
        self.queries = []

    def row(self, site, stamp, count, hour=None):
        raw = {"sitecode": site, "directionname": "north", "lanecode": 1,
               "datetimefrom": stamp.isoformat(), "total": count,
               "weekday": self.now.weekday(), "hourfrom": self.now.hour if hour is None else hour}
        return {"station_id": site, "metric": "total", "observed_at": stamp.isoformat(),
                "observation_key": f"{site}-{stamp.isoformat()}-{raw['hourfrom']}",
                "dimensions": {"directionname": "north", "lanecode": 1}, "raw_record": raw}

    def database(self, _url, _key, table, query):
        self.assertEqual(table, "observations")
        if query["source_id"] != "eq.basel_dataset_100006":
            return []
        self.queries.append(query)
        rows = self.rows
        for field, condition in query.items():
            if not condition.startswith(("eq.", "lt.")) or field == "source_id":
                continue

            def value(row):
                if "->>" in field:
                    column, key = field.split("->>")
                    return (row.get(column) or {}).get(key)
                return row.get(field)

            if condition.startswith("eq."):
                rows = [row for row in rows if str(value(row)) == condition[3:]]
            else:
                boundary = datetime.fromisoformat(condition[3:])
                rows = [row for row in rows if datetime.fromisoformat(value(row)) < boundary]
        rows = sorted(rows, key=lambda row: row["observed_at"], reverse=True)
        offset, limit = int(query.get("offset", 0)), int(query["limit"])
        return rows[offset:offset + limit]

    def fetch(self, counters=()):
        with patch("risk_assessment.supabase_data._credentials", return_value=("https://example.test", "example-key")), \
                patch("risk_assessment.supabase_data._weather_snapshot", return_value={}), \
                patch("risk_assessment.supabase_data._latest_run", return_value={"request_ok": True, "raw_payload": {}}), \
                patch("risk_assessment.supabase_data._get_json", side_effect=self.database):
            return fetch_supabase_sources(traffic_counters=counters)["basel_dataset_100006"]

    def test_dashboard_reads_latest_context_without_loading_archive(self):
        snapshot = self.fetch()
        self.assertEqual(len(snapshot["data"]["results"]), TRAFFIC_CONTEXT_LIMIT)
        self.assertEqual(snapshot["history_results"], [])
        self.assertEqual(len(self.queries), 1)
        self.assertEqual(self.queries[0]["metric"], "eq.total")

    def test_observation_reader_has_a_finite_default(self):
        with patch("risk_assessment.supabase_data._get_json", side_effect=self.database):
            rows = _observations("https://example.test", "example-key", "basel_dataset_100006")
        self.assertEqual(len(rows), 500)
        self.assertEqual(len(self.queries), 1)

    def test_selected_counter_is_found_even_outside_context_window(self):
        current_at = self.now - timedelta(minutes=30)
        self.rows.append(self.row("route-site", current_at, 1000))
        self.rows.extend(self.row("route-site", current_at - timedelta(weeks=week), 100)
                         for week in range(1, 71))
        self.rows.extend(self.row("route-site", current_at - timedelta(weeks=week), 9999, hour=-1)
                         for week in range(1, 71))
        snapshot = self.fetch((self.counter, self.counter))
        history = snapshot["history_results"]
        self.assertEqual(len(history), 1 + TRAFFIC_BASELINE_LIMIT)
        self.assertTrue(all(row["sitecode"] == "route-site" and row["hourfrom"] == self.now.hour
                            for row in history))
        self.assertEqual(len(self.queries), 3)  # Context + one current + one baseline query.
        finding = detect_traffic_disturbance(route_counters=(self.counter,), snapshot=snapshot,
                                             historical_records=history)
        self.assertEqual(finding.status, "detected")
        self.assertGreater(finding.robust_z, 3)
        reference = detect_traffic_disturbance(
            route_counters=(self.counter,), snapshot=snapshot,
            historical_records=[row["raw_record"] for row in self.rows],
        )
        self.assertEqual(finding.robust_z, reference.robust_z)

    def test_small_baseline_stays_unknown(self):
        self.rows.append(self.row("route-site", self.now, 1000))
        self.rows.extend(self.row("route-site", self.now - timedelta(weeks=week), 100)
                         for week in range(1, 4))
        snapshot = self.fetch((self.counter,))
        finding = detect_traffic_disturbance(route_counters=(self.counter,), snapshot=snapshot,
                                             historical_records=snapshot["history_results"])
        self.assertEqual(finding.status, "unknown")
        self.assertIsNone(finding.robust_z)

    def test_cli_passes_selected_counters_and_reuses_loaded_sources(self):
        args = build_parser().parse_args(["--traffic-counter", "route-site|north|1"])
        with patch("risk_assessment.cli.fetch_supabase_sources", return_value={}) as fetch:
            self.assertEqual(_supabase_sources_for(args), {})
            self.assertEqual(_supabase_sources_for(args), {})
        fetch.assert_called_once_with(traffic_counters=(self.counter,))


if __name__ == "__main__":
    unittest.main()
