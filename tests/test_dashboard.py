"""Dashboard provenance and repeatable operator demo cases."""

from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from contextlib import redirect_stdout
from io import StringIO
import json
import sys
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

from risk_assessment.dashboard import demo_dashboard, live_dashboard
from risk_assessment.demo import demo_fleet
from risk_assessment.server import (
    COLLECTOR_SCRIPT, PROJECT_ROOT, DashboardHandler, dashboard_request,
    main as server_main, start_collector, stop_collector,
)


class DemoFleetTests(unittest.TestCase):
    def setUp(self):
        self.anchor = datetime(2026, 10, 3, 10, tzinfo=timezone.utc)

    def test_requested_actions_use_existing_backend_policy(self):
        expected = {"normal": "normal", "traffic": "buffer", "urgent": "expedite",
                    "heat": "quality_review", "reroute": "reroute"}
        for scenario, action in expected.items():
            with self.subTest(scenario=scenario):
                shipment = demo_fleet(self.anchor, scenario=scenario)["shipments"][0]
                self.assertEqual(shipment["action"], action)
                self.assertEqual(shipment["score"]["coverage_percent"], 100)
                self.assertEqual(shipment["score"]["minimum"], shipment["score"]["maximum"])

    def test_quality_hold_has_no_score_threshold(self):
        shipment = demo_fleet(self.anchor)["shipments"][3]
        self.assertEqual(shipment["action"], "quality_review")
        self.assertLess(shipment["score"]["minimum"], 10)
        self.assertGreater(shipment["thermal"]["minutes_above_max"], 0)

    def test_jam_freezes_position_but_keeps_delay_in_eta(self):
        start = demo_fleet(self.anchor, 0, "urgent")["shipments"][0]
        later = demo_fleet(self.anchor, 20, "urgent")["shipments"][0]
        self.assertEqual(start["status"], "delayed")
        self.assertEqual(start["progress"], later["progress"])
        self.assertEqual(start["etaAt"], later["etaAt"])
        self.assertEqual(start["slackMinutes"], 10)

    def test_temperature_hold_stops_the_demo_truck_and_keeps_monitoring(self):
        start = demo_fleet(self.anchor)["shipments"][3]
        later = demo_fleet(self.anchor, 60)["shipments"][3]
        self.assertEqual(start["status"], "held")
        self.assertEqual(later["status"], "held")
        self.assertEqual(start["progress"], later["progress"])
        self.assertGreater(later["temperatureC"], start["temperatureC"])
        self.assertGreater(later["observedAt"], start["observedAt"])

    def test_clear_route_moves_and_finishes_without_looping(self):
        start = demo_fleet(self.anchor, 0, "normal")["shipments"][0]
        later = demo_fleet(self.anchor, 20, "normal")["shipments"][0]
        completed = demo_fleet(self.anchor, 180, "normal")["shipments"][0]
        self.assertGreater(later["progress"], start["progress"])
        self.assertLess(later["remainingKm"], start["remainingKm"])
        self.assertEqual(completed["status"], "delivered")
        self.assertEqual(completed["progress"], 1)
        self.assertEqual(completed["remainingKm"], 0)

    def test_restart_is_repeatable_and_does_not_fetch_live_sources(self):
        with patch("risk_assessment.dashboard.fetch_supabase_sources") as fetch:
            self.assertEqual(demo_dashboard(self.anchor), demo_dashboard(self.anchor))
        fetch.assert_not_called()

    def test_reroute_never_uses_an_alternative_eta_in_the_past(self):
        data = demo_fleet(self.anchor, 60, "reroute")["shipments"][0]
        self.assertGreater(datetime.fromisoformat(data["alternateEtaAt"]), self.anchor + timedelta(minutes=60))

    def test_bad_replay_inputs_are_rejected(self):
        for value in (-1, 181, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                demo_fleet(self.anchor, value)
        with self.assertRaises(ValueError):
            demo_fleet(self.anchor, scenario="unknown")


class LiveDashboardTests(unittest.TestCase):
    def test_confirmed_events_precede_unknown_validity_and_only_current_events_are_mapped(self):
        now = datetime(2026, 10, 3, 12, tzinfo=timezone.utc)
        stamp = now.isoformat()
        point = {"latitude": 47.56, "longitude": 7.6}
        events = [{"id": "unknown", "descriptions": ["Uncertain"], "local_coordinates": [point]},
                  {"id": "active", "descriptions": ["Current jam"], "local_coordinates": [point],
                   "validity_status": "active", "valid_from": stamp, "updated_at": stamp},
                  {"id": "expired", "valid_until": (now - timedelta(minutes=1)).isoformat()},
                  {"id": "future", "valid_from": (now + timedelta(days=1)).isoformat()}]
        result = live_dashboard({"opentransportdata_basel_region": {"request_ok": True,
                                "data": {"fetched_at": stamp, "traffic_situations": events}}}, now=now)
        self.assertEqual([alert["id"] for alert in result["alerts"]], ["active", "unknown"])
        self.assertEqual([point["id"] for point in result["locations"] if point["category"] == "traffic"],
                         ["traffic-active"])
        self.assertEqual(result["signals"][1]["value"], 1)

    def test_live_has_only_supabase_signals_and_no_synthetic_shipments(self):
        now = datetime.now(timezone.utc)
        stamp = now.isoformat()
        sources = {
            "meteoswiss_basel_temperature": {"request_ok": True, "data": {"station": {
                "observed_at": stamp, "measurements": {"tre200s0": 33, "fu3010z1": 61}}}},
            "opentransportdata_basel_region": {"request_ok": True, "data": {
                "fetched_at": stamp, "traffic_situations": [], "errors": []}},
        }
        with patch("risk_assessment.local_data.read_snapshot", side_effect=AssertionError("local archive used")):
            result = live_dashboard(sources, now=now)
        self.assertEqual(result["mode"], "live")
        self.assertEqual(result["shipments"], [])
        self.assertIsNone(result["simulation"])
        self.assertEqual(result["signals"][0]["value"], 33)
        self.assertEqual(result["signals"][0]["severity"], "warning")
        self.assertEqual(result["signals"][3]["freshness"], "unknown")

    def test_stale_weather_does_not_get_an_active_warning(self):
        stamp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        result = live_dashboard({"meteoswiss_basel_temperature": {"request_ok": True,
                                "data": {"station": {"observed_at": stamp, "measurements": {"tre200s0": 40}}}}})
        self.assertEqual(result["signals"][0]["freshness"], "stale")
        self.assertEqual(result["signals"][0]["severity"], "unknown")

    def test_future_weather_is_unknown(self):
        stamp = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        result = live_dashboard({"meteoswiss_basel_temperature": {"request_ok": True,
                                "data": {"station": {"observed_at": stamp, "measurements": {"tre200s0": 40}}}}})
        self.assertEqual(result["signals"][0]["freshness"], "unknown")
        self.assertEqual(result["signals"][0]["severity"], "unknown")

    def test_failed_live_fetch_is_not_replaced_by_demo(self):
        with patch("risk_assessment.server.live_dashboard", side_effect=ValueError("unavailable")), \
                patch("risk_assessment.server._live_cached", None):
            with self.assertRaises(ValueError):
                dashboard_request({"mode": ["live"]})


class DashboardHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_http_demo_returns_complete_json(self):
        with urlopen(self.base + "/api/dashboard?mode=demo&scenario=urgent") as response:
            payload = json.load(response)
            self.assertEqual(response.status, 200)
            self.assertEqual(payload["shipments"][0]["action"], "expedite")

    def test_bad_query_is_400(self):
        for query in ("mode=invalid", "elapsedMinutes=nan", "scenario=invalid", "anchor=not-a-time"):
            with self.subTest(query=query), self.assertRaises(HTTPError) as result:
                urlopen(self.base + "/api/dashboard?" + query)
            self.assertEqual(result.exception.code, 400)
            result.exception.close()

    def test_live_error_is_503_without_leaking_provider_error(self):
        with patch("risk_assessment.server.live_dashboard", side_effect=ValueError("provider detail")), \
                patch("risk_assessment.server._live_cached", None):
            with self.assertRaises(HTTPError) as result:
                urlopen(self.base + "/api/dashboard?mode=live")
        self.assertEqual(result.exception.code, 503)
        self.assertNotIn("provider detail", result.exception.read().decode())
        result.exception.close()

    def test_server_collector_uses_the_running_python_and_stops_with_server(self):
        with patch("risk_assessment.server.subprocess.Popen") as launch:
            process = start_collector()
        launch.assert_called_once_with([sys.executable, str(COLLECTOR_SCRIPT)], cwd=PROJECT_ROOT)
        process.poll.return_value = None
        stop_collector(process)
        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=5)

    def test_server_starts_collector_by_default_but_can_use_an_existing_one(self):
        with patch("risk_assessment.server.ThreadingHTTPServer") as server, \
                patch("risk_assessment.server.start_collector") as launch, \
                patch("risk_assessment.server.stop_collector") as stop, \
                patch("sys.argv", ["server.py"]), redirect_stdout(StringIO()):
            server_main()
        server.return_value.serve_forever.assert_called_once_with()
        launch.assert_called_once_with()
        stop.assert_called_once_with(launch.return_value)

        with patch("risk_assessment.server.ThreadingHTTPServer"), \
                patch("risk_assessment.server.start_collector") as launch, \
                patch("sys.argv", ["server.py", "--no-collector"]), redirect_stdout(StringIO()):
            server_main()
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
