"""Offline checks that failed fetches preserve the last successful response."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import api_requester
import transform_port_pegel


class ApiArchiveTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.data_dir = self.root / "data"
        self.enterContext(patch.object(api_requester, "ROOT", self.root))
        self.enterContext(patch.object(api_requester, "DATA_DIR", self.data_dir))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def fetch(self, source, response, timestamp):
        with (
            patch.object(api_requester, "read_response", return_value=response),
            patch.object(api_requester, "now_utc", return_value=timestamp),
        ):
            return api_requester.check_source(source)

    def test_failures_preserve_latest_and_raw_and_extend_history(self):
        html_source = next(s for s in api_requester.SOURCES if s["kind"] == "html")
        json_source = next(s for s in api_requester.SOURCES if s["kind"] == "json")
        meteo_source = next(s for s in api_requester.SOURCES if s["kind"] == "meteo_current")
        meteo_body = b"Station/Location;Date;tre200s0\nBAS;202610030800;15.2\n"
        for source, body in (
            (html_source, b"<html><body>Water levels</body></html>"),
            (json_source, b'{"results": [{"value": 12}]}'),
            (meteo_source, meteo_body),
        ):
            with self.subTest(source=source["id"]):
                result = self.fetch(source, (200, {}, body, None), "2026-10-03T08:00:00+00:00")
                self.assertTrue(result["request_ok"])
                folder = self.data_dir / source["id"]
                latest_path = folder / "latest.json"
                latest = latest_path.read_bytes()
                raw_before = {p.name: p.read_bytes() for p in (folder / "raw").glob("*")}
                for response in (
                    (None, {}, None, "Network unavailable"),
                    (503, {}, b"Service unavailable", "HTTP 503"),
                    (429, {"Retry-After": "60"}, b"Rate limited", "HTTP 429"),
                ):
                    self.fetch(source, response, "2026-10-03T08:10:00+00:00")
                    self.assertEqual(latest_path.read_bytes(), latest)
                    self.assertEqual(
                        {p.name: p.read_bytes() for p in (folder / "raw").glob("*")}, raw_before,
                    )
                    error = json.loads((folder / "last_error.json").read_text())
                    self.assertEqual(error["http_status"], response[0])
                    self.assertEqual(error["error"], response[3])
                    self.assertEqual(error["checked_at"], "2026-10-03T08:10:00+00:00")
                history = [json.loads(line) for line in (folder / "history.jsonl").read_text().splitlines()]
                self.assertEqual(len(history), 4)
                self.assertEqual([r["request_ok"] for r in history], [True, False, False, False])

    def test_first_failed_fetch_does_not_create_latest_or_raw(self):
        source = next(s for s in api_requester.SOURCES if s["kind"] == "html")
        self.fetch(source, (503, {}, b"Unavailable", "HTTP 503"), "2026-10-03T08:00:00+00:00")
        folder = self.data_dir / source["id"]
        self.assertFalse((folder / "latest.json").exists())
        self.assertFalse((folder / "raw").exists())
        self.assertTrue((folder / "last_error.json").exists())
        self.assertEqual(len((folder / "history.jsonl").read_text().splitlines()), 1)

    def test_save_failure_after_failed_fetch_does_not_overwrite_latest(self):
        source = next(s for s in api_requester.SOURCES if s["kind"] == "json")
        self.fetch(source, (200, {}, b'{"value": 12}', None), "2026-10-03T08:00:00+00:00")
        latest = self.data_dir / source["id"] / "latest.json"
        previous_bytes = latest.read_bytes()
        with patch.object(api_requester, "save_result", side_effect=OSError("Disk full")):
            result = self.fetch(source, (None, {}, None, "Network unavailable"), "2026-10-03T08:10:00+00:00")
        self.assertFalse(result["saved"])
        self.assertEqual(latest.read_bytes(), previous_bytes)

    def test_success_after_failure_updates_latest(self):
        source = next(s for s in api_requester.SOURCES if s["kind"] == "json")
        self.fetch(source, (None, {}, None, "Network unavailable"), "2026-10-03T08:00:00+00:00")
        self.fetch(source, (200, {}, b'{"value": 13}', None), "2026-10-03T08:10:00+00:00")
        folder = self.data_dir / source["id"]
        latest = json.loads((folder / "latest.json").read_text())
        self.assertEqual(latest["data"], {"value": 13})
        self.assertEqual(latest["checked_at"], "2026-10-03T08:10:00+00:00")
        self.assertEqual(len((folder / "history.jsonl").read_text().splitlines()), 2)

    def test_once_then_network_failure_preserves_all_latest_pages(self):
        current_html = (
            "<table><tr><th>Gewässer/See</th><th>Aktueller Wert</th><th>Zeit</th></tr>"
            "<tr><td>Basel</td><td>250 cm</td><td>08:00</td></tr></table>"
        ).encode()
        forecast_html = (
            "<table><tr><th>Datum - Zeit</th><th>Pegel</th><th>Abfluss</th></tr>"
            "<tr><td>03.10.2026 09:00</td><td>250.1</td><td>500</td></tr></table>"
        ).encode()

        def successful_response(source):
            if source["kind"] == "meteo_current":
                body = b"Station/Location;Date;tre200s0\nBAS;202610030800;15.2\n"
            elif source["kind"] == "json":
                body = b'{"results": []}'
            elif source["id"] == "port_pegel_current":
                body = current_html
            else:
                body = forecast_html
            return 200, {}, body, None

        output = io.StringIO()
        with (
            patch.object(transform_port_pegel, "ROOT", self.root),
            patch.object(transform_port_pegel, "DATA_DIR", self.data_dir),
            patch.object(transform_port_pegel, "OUTPUT_DIR", self.data_dir / "port_pegel_clean"),
            patch.object(api_requester.time, "sleep"),
            patch.object(sys, "argv", ["api_requester.py", "--once"]),
            contextlib.redirect_stdout(output),
        ):
            with (
                patch.object(api_requester, "read_response", side_effect=successful_response),
                patch.object(api_requester, "now_utc", return_value="2026-10-03T08:00:00+00:00"),
            ):
                self.assertEqual(api_requester.main(), 0)
            latest_before = {
                source["id"]: (self.data_dir / source["id"] / "latest.json").read_bytes()
                for source in api_requester.SOURCES
            }
            raw_before = {p.relative_to(self.root): p.read_bytes() for p in self.data_dir.glob("*/raw/*")}
            with (
                patch.object(api_requester, "urlopen", side_effect=URLError("Network unavailable")),
                patch.object(api_requester, "now_utc", return_value="2026-10-03T08:10:00+00:00"),
            ):
                self.assertEqual(api_requester.main(), 0)

        for source in api_requester.SOURCES:
            folder = self.data_dir / source["id"]
            self.assertEqual((folder / "latest.json").read_bytes(), latest_before[source["id"]])
            self.assertTrue((folder / "last_error.json").exists())
            self.assertEqual(len((folder / "history.jsonl").read_text().splitlines()), 2)
        self.assertEqual(
            {p.relative_to(self.root): p.read_bytes() for p in self.data_dir.glob("*/raw/*")}, raw_before,
        )
        cleaned = json.loads((self.data_dir / "port_pegel_clean" / "latest.json").read_text())
        self.assertEqual(cleaned["current_page_checked_at"], "2026-10-03T08:00:00+00:00")
        self.assertEqual(cleaned["forecast_page_checked_at"], "2026-10-03T08:00:00+00:00")
        self.assertEqual(output.getvalue().count("Clean port data saved:"), 2)


if __name__ == "__main__":
    unittest.main()
