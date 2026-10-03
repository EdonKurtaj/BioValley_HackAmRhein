"""Traffic-only polling uses the same durable database ingestion as the collector."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import api_requester
import opentransportdata
from normalize_observations import normalize
from supabase_ingest import SupabaseError, SupabaseIngestor, SupabaseRestClient


def snapshot():
    return {
        "fetched_at": "2026-10-03T18:01:00Z", "errors": [],
        "traffic_situations": [{"id": "event-1", "type": "RoadWorks", "filter_match": "coordinates", "descriptions": ["Road works"]}],
        "traffic_counters": {
            "sites": [{"id": "counter-1", "coordinates": [], "lanes": 2}],
            "current_readings": [{"site_id": "counter-1", "observed_at": "2026-10-03T18:00:00Z",
                "values": [
                    {"index": "1", "meaning": "all_vehicles_flow_per_hour", "fields": {"vehicleFlowRate": "0"}},
                    {"index": "2", "meaning": "all_vehicles_average_speed_kmh", "fields": {"speed": "72.5"}},
                    {"index": "3", "meaning": None, "fields": {}},
                ]}],
        },
    }


class TrafficIngestionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.enterContext(patch.object(api_requester, "ROOT", self.root))
        self.enterContext(patch.object(api_requester, "DATA_DIR", self.root / "data"))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(contextlib.redirect_stderr(io.StringIO()))
        self.enterContext(patch.object(opentransportdata, "save_snapshot", return_value=1))
        self.source = next(s for s in api_requester.SOURCES if s["kind"] == "opentransportdata")

    def test_standalone_poll_delivers_numeric_rows_and_preserves_events(self):
        client = MagicMock()
        ingestor = SupabaseIngestor(client, self.root / "outbox")
        with patch.object(opentransportdata, "fetch_all", return_value=snapshot()) as fetch:
            code, _ = opentransportdata.run_once(ingestor=ingestor)
        fetch.assert_called_once_with(False)
        self.assertEqual(code, 0)
        batch = client.write_batch.call_args.args[0]
        self.assertEqual(batch["source"]["kind"], "opentransportdata")
        self.assertEqual(batch["fetch_run"]["raw_payload"]["traffic_situations"], snapshot()["traffic_situations"])
        self.assertEqual([(r["value"], r["unit"]) for r in batch["observations"]], [(0, "vehicles/hour"), (72.5, "km/h")])
        self.assertTrue(all(r["observed_at"] == "2026-10-03T18:00:00+00:00" for r in batch["observations"]))
        self.assertEqual(list(ingestor.outbox.glob("*.json")), [])

    def test_database_rejection_keeps_batch_for_next_retry(self):
        client = MagicMock()
        client.write_batch.side_effect = SupabaseError("HTTP 400")
        ingestor = SupabaseIngestor(client, self.root / "outbox")
        with patch.object(opentransportdata, "fetch_all", return_value=snapshot()):
            self.assertEqual(opentransportdata.run_once(ingestor=ingestor)[0], 0)
        pending = list(ingestor.outbox.glob("*.json"))
        self.assertEqual(len(pending), 1)
        run_id = json.loads(pending[0].read_text())["fetch_run"]["id"]
        client.write_batch.side_effect = None
        ingestor.flush()
        self.assertEqual(client.write_batch.call_args.args[0]["fetch_run"]["id"], run_id)
        self.assertEqual(list(ingestor.outbox.glob("*.json")), [])

    def test_failed_feed_is_logged_without_measurements(self):
        payload = snapshot()
        payload["errors"] = ["Traffic Counters: HTTP 503"]
        result = api_requester.check_opentransportdata(self.source, snapshot=payload)
        client = MagicMock()
        SupabaseIngestor(client, self.root / "outbox").ingest(self.source, result)
        batch = client.write_batch.call_args.args[0]
        self.assertFalse(batch["fetch_run"]["request_ok"])
        self.assertEqual(batch["observations"], [])

    def test_measurement_identity_is_stable_across_fetches(self):
        result = api_requester.check_opentransportdata(self.source, snapshot=snapshot())
        rows = normalize(result)
        result["checked_at"] = "2026-10-03T18:02:00Z"
        self.assertEqual(rows, normalize(result))

    def test_constraint_error_names_migration_without_echoing_payload(self):
        details = {"code": "23514", "message": "data_sources_source_kind_check", "details": "private diagnostic"}
        error = HTTPError("https://example.com", 400, "bad request", {}, io.BytesIO(json.dumps(details).encode()))
        with patch("supabase_ingest.urlopen", side_effect=error):
            with self.assertRaises(SupabaseError) as caught:
                SupabaseRestClient("https://example.com", "example-key").request("data_sources", [])
        self.assertIn("20261003190000_allow_opentransportdata_source_kind.sql", str(caught.exception))
        self.assertNotIn("private diagnostic", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
