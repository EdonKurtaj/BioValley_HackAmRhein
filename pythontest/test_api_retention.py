"""Bound HTML archives without deleting the latest referenced page."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import api_requester


class RawRetentionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.enterContext(patch.object(api_requester, "ROOT", self.root))
        self.enterContext(patch.object(api_requester, "DATA_DIR", self.root / "data"))
        self.source = next(s for s in api_requester.SOURCES if s["kind"] == "html")
        self.folder = self.root / "data" / self.source["id"]

    def save(self, timestamp):
        result = {"request_ok": True, "checked_at": timestamp, "data": {}}
        api_requester.save_result(self.source, result, b"<html>Saved page</html>")
        return self.root / result["data"]["raw_html_file"]

    def test_more_than_keep_runs_leave_exactly_latest_n_files(self):
        start = datetime(2026, 10, 3, tzinfo=timezone.utc)
        saved = [self.save((start + timedelta(minutes=10 * i)).isoformat())
                 for i in range(api_requester.RAW_KEEP + 10)]
        remaining = set((self.folder / "raw").glob("*.html"))
        self.assertEqual(len(remaining), api_requester.RAW_KEEP)
        self.assertEqual(remaining, set(saved[-api_requester.RAW_KEEP:]))
        record = json.loads((self.folder / "latest.json").read_text())
        self.assertTrue((self.root / record["data"]["raw_html_file"]).is_file())
        self.assertEqual(len((self.folder / "history.jsonl").read_text().splitlines()), len(saved))

    def test_latest_reference_is_protected_if_clock_moves_backwards(self):
        with patch.object(api_requester, "RAW_KEEP", 3):
            newer = [self.save(f"2026-10-03T0{i}:00:00+00:00") for i in (1, 2, 3)]
            latest = self.save("2026-10-02T00:00:00+00:00")
        self.assertEqual(set((self.folder / "raw").glob("*.html")), {latest, newer[1], newer[2]})
        self.assertTrue(latest.is_file())

    def test_failed_latest_write_does_not_prune_previous_reference(self):
        with patch.object(api_requester, "RAW_KEEP", 1):
            previous_raw = self.save("2026-10-03T01:00:00+00:00")
            latest_path = self.folder / "latest.json"
            previous_record = latest_path.read_bytes()
            original_write = Path.write_text

            def write_text(path, *args, **kwargs):
                if path == latest_path:
                    raise OSError("Cannot update latest")
                return original_write(path, *args, **kwargs)

            with patch.object(Path, "write_text", new=write_text):
                with self.assertRaises(OSError):
                    self.save("2026-10-03T02:00:00+00:00")
        self.assertTrue(previous_raw.is_file())
        self.assertEqual(latest_path.read_bytes(), previous_record)


if __name__ == "__main__":
    unittest.main()
