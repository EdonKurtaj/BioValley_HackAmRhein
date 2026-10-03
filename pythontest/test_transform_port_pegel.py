"""Offline regression checks for unavailable saved port pages."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import api_requester
import transform_port_pegel


class SavedPortPageTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.data_dir = self.root / "data"
        self.latest = self.data_dir / "port_pegel_current" / "latest.json"
        self.latest.parent.mkdir(parents=True)
        self.enterContext(patch.object(transform_port_pegel, "ROOT", self.root))
        self.enterContext(patch.object(transform_port_pegel, "DATA_DIR", self.data_dir))

    def write_record(self, record):
        self.latest.write_text(json.dumps(record), encoding="utf-8")

    def test_transform_rejects_unavailable_html_path(self):
        for record in ({"data": None}, {}, {"data": {}}, {"data": {"raw_html_file": ""}}):
            with self.subTest(record=record):
                self.write_record(record)
                with self.assertRaisesRegex(RuntimeError, "No saved HTML path.*check the fetch"):
                    transform_port_pegel.transform()

    def test_transform_rejects_missing_html_file(self):
        self.write_record({"data": {"raw_html_file": "data/missing.html"}})
        with self.assertRaisesRegex(RuntimeError, "Saved HTML file.*missing.html.*check the fetch"):
            transform_port_pegel.transform()

    def test_latest_page_reads_existing_html(self):
        html_path = self.root / "page.html"
        html_path.write_text("<html>Saved page</html>", encoding="utf-8")
        record = {"data": {"raw_html_file": "page.html"}}
        self.write_record(record)
        actual_record, html = transform_port_pegel.latest_page("port_pegel_current")
        self.assertEqual(actual_record, record)
        self.assertEqual(html, "<html>Saved page</html>")

    def test_run_cycle_reports_failure_and_can_run_again(self):
        self.write_record({"data": None})
        output = io.StringIO()
        with (
            patch.object(api_requester, "check_source", return_value={"saved": True}) as check,
            patch.object(api_requester.time, "sleep"),
            contextlib.redirect_stdout(output),
        ):
            first_results = api_requester.run_cycle()
            second_results = api_requester.run_cycle()
        self.assertEqual(len(first_results), len(api_requester.SOURCES))
        self.assertEqual(len(second_results), len(api_requester.SOURCES))
        self.assertEqual(check.call_count, 2 * len(api_requester.SOURCES))
        self.assertEqual(output.getvalue().count("Clean port data: FAILED —"), 2)


if __name__ == "__main__":
    unittest.main()
