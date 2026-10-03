"""Offline ingestion, idempotency, and failure recovery tests."""

import contextlib
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import api_requester
import supabase_ingest
from interfaces import FetchRun, Observation
from normalize_observations import normalize, utc_time
from supabase_ingest import SupabaseError, SupabaseIngestor, SupabaseRestClient


def fetch_result(source_id="basel_dataset_100089", success=True):
    return {
        "source_id": source_id, "checked_at": "2026-10-03T10:00:00+00:00",
        "http_status": 200 if success else 503, "request_ok": success,
        "rate_limited": False, "retry_after": None, "response_bytes": 100,
        "error": None if success else "HTTP 503",
        "data": {"results": [{"timestamp": "2026-10-03T09:55:00Z", "abfluss": 338.5,
                              "pegelhoehe": 478, "pegel": 244.78}]} if success else None,
    }


class NormalizationTests(unittest.TestCase):
    def test_rhine_units_and_stable_identity(self):
        result = fetch_result()
        rows = normalize(result)
        self.assertEqual(len(rows), 3)
        self.assertEqual({r["metric"]: r["unit"] for r in rows},
                         {"abfluss": "m3/s", "pegelhoehe": "cm", "pegel": "m"})
        result["checked_at"] = "2026-10-03T10:10:00Z"
        self.assertEqual(rows, normalize(result))
        self.assertEqual(rows[0]["observed_at"], "2026-10-03T09:55:00+00:00")

    def test_failed_fetch_has_no_observations(self):
        self.assertEqual(normalize(fetch_result(success=False)), [])

    def test_traffic_lanes_are_distinct_and_zero_is_preserved(self):
        result = fetch_result("basel_dataset_100006")
        base = {"sitecode": "403", "datetimefrom": "2026-10-03T09:00:00Z",
                "datetimeto": "2026-10-03T10:00:00Z", "directionname": "North", "total": 0}
        result["data"] = {"results": [dict(base, lanecode=1), dict(base, lanecode=2)]}
        rows = normalize(result)
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["observation_key"], rows[1]["observation_key"])
        self.assertEqual([r["value"] for r in rows], [0, 0])

    def test_meteo_uses_observation_time_not_fetch_time(self):
        result = fetch_result("meteoswiss_basel_temperature")
        result["data"] = {"station": {"station_id": "BAS", "station_name": "Basel / Binningen",
                            "observed_at_utc": "2026-10-03T09:40:00Z", "measurements": {"tre200s0": 17.3}},
                          "parameter_metadata": {"tre200s0": {"unit": "°C"}}}
        row = normalize(result)[0]
        self.assertEqual(row["observed_at"], "2026-10-03T09:40:00+00:00")
        self.assertEqual((row["station_id"], row["metric"], row["unit"]), ("BAS", "tre200s0", "°C"))

    def test_current_port_times_use_zurich(self):
        result = fetch_result("port_pegel_current")
        result["data"] = {"tables": [[["Gewässer/See", "Aktueller Wert", "Zeit"],
                                      ["Basel", "478 cm", "03.10.2026 11:40"]]]}
        self.assertEqual(normalize(result)[0]["observed_at"], "2026-10-03T09:40:00+00:00")

    def test_forecast_winter_time_and_revision_identity(self):
        result = fetch_result("port_pegel_forecast")
        text = ("Ausgegeben am / Emission: 3.10.2026, 09.26 h MEWZ / HHEC "
                "Meteolauf von / Prévision météo de: 3.10.2026, 00.00 h UTC "
                "Gemessene Werte bis / Valeurs mesurées jusqu'au: 3.10.2026, 08.00 "
                "Übrige Zeitangaben in / Autres valeurs de temps en : MEWZ / HHEC "
                "Stundenmittel des Wasserstandes")
        result["data"] = {"tables": [[["Datum - Zeit", "Pegel", "Abfluss"],
                                      ["03.10.2026 - 10:00", "244.83", "373.1"]]], "text": text}
        rows = normalize(result)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["observed_at"], "2026-10-03T09:00:00+00:00")
        self.assertEqual(rows[0]["dimensions"]["issued_at"], "2026-10-03T08:26:00+00:00")
        result["data"]["text"] = text.replace("09.26", "10.26")
        self.assertNotEqual(rows[0]["observation_key"], normalize(result)[0]["observation_key"])

    def test_dst_boundary_and_ambiguous_time(self):
        self.assertEqual(utc_time("25.10.2026 01:30"), "2026-10-24T23:30:00+00:00")
        self.assertEqual(utc_time("25.10.2026 03:30"), "2026-10-25T02:30:00+00:00")
        with self.assertRaises(ValueError):
            utc_time("25.10.2026 02:30")


class IngestionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.output = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.client = MagicMock()
        self.ingestor = SupabaseIngestor(self.client, self.root / "outbox")
        self.source = next(s for s in api_requester.SOURCES if s["id"] == "basel_dataset_100089")

    def test_each_attempt_is_logged_and_links_observations(self):
        self.ingestor.ingest(self.source, fetch_result())
        batch = self.client.write_batch.call_args.args[0]
        self.assertEqual(len(batch["observations"]), 3)
        self.assertTrue(all(row["fetch_run_id"] == batch["fetch_run"]["id"] for row in batch["observations"]))
        self.assertFalse(list(self.ingestor.outbox.glob("*.json")))
        self.ingestor.ingest(self.source, fetch_result(success=False))
        batch = self.client.write_batch.call_args.args[0]
        self.assertFalse(batch["fetch_run"]["request_ok"])
        self.assertEqual(batch["observations"], [])

    def test_retry_uses_same_fetch_uuid_and_removes_pending_only_on_success(self):
        self.client.write_batch.side_effect = SupabaseError("Unavailable")
        with self.assertRaises(SupabaseError):
            self.ingestor.ingest(self.source, fetch_result())
        pending = next(self.ingestor.outbox.glob("*.json"))
        original = json.loads(pending.read_text())
        self.client.write_batch.side_effect = None
        self.ingestor.flush()
        self.assertEqual(self.client.write_batch.call_args.args[0], original)
        self.assertFalse(pending.exists())

    def test_normalization_error_still_logs_attempt_and_raw_payload(self):
        result = fetch_result()
        result["data"] = {"results": [{"unexpected": True}]}
        self.ingestor.ingest(self.source, result)
        batch = self.client.write_batch.call_args.args[0]
        self.assertEqual(batch["fetch_run"]["raw_payload"], result["data"])
        self.assertIn("Normalization", batch["fetch_run"]["error"])
        self.assertEqual(batch["observations"], [])
        self.assertTrue(batch["fetch_run"]["request_ok"])  # HTTP success remains distinct from normalization.
        self.assertNotIn("OK — fetch logged", self.output.getvalue())

    def test_partial_database_write_retries_without_duplicate_fetches(self):
        class MemoryClient(SupabaseRestClient):
            def __init__(self):
                self.tables = {table: {} for table in ("data_sources", "fetch_runs", "observations")}
                self.fail_observations = False

            def request(self, table, rows=None, conflict=None, query=None):
                if table == "observations" and self.fail_observations:
                    raise SupabaseError("Observation write interrupted")
                for row in rows:
                    if table == "observations":
                        assert row["fetch_run_id"] in self.tables["fetch_runs"]
                        key = tuple(row[field] for field in conflict.split(","))
                    else:
                        key = row["id"]
                    self.tables[table][key] = row

        client = MemoryClient()
        ingestor = SupabaseIngestor(client, self.root / "outbox")
        client.fail_observations = True
        with self.assertRaises(SupabaseError):
            ingestor.ingest(self.source, fetch_result())
        self.assertEqual(len(client.tables["fetch_runs"]), 1)
        client.fail_observations = False
        ingestor.flush()
        self.assertEqual(len(client.tables["fetch_runs"]), 1)
        self.assertEqual(len(client.tables["observations"]), 3)
        ingestor.ingest(self.source, fetch_result())
        self.assertEqual(len(client.tables["fetch_runs"]), 2)
        self.assertEqual(len(client.tables["observations"]), 3)

    def test_collector_logs_unexpected_source_exceptions_and_continues(self):
        sink = MagicMock()
        sources = api_requester.SOURCES[:2]
        with (
            patch.object(api_requester, "SOURCES", sources),
            patch.object(api_requester, "check_source", side_effect=[TypeError("Bad source"), fetch_result()]),
            patch.object(api_requester.time, "sleep"),
            patch("transform_port_pegel.transform", side_effect=RuntimeError("No local HTML")),
        ):
            api_requester.run_cycle(sink)
        self.assertEqual(sink.ingest.call_count, 2)
        first = sink.ingest.call_args_list[0].args[1]
        self.assertFalse(first["request_ok"])
        self.assertIn("TypeError", first["error"])

    def test_database_failure_does_not_stop_remaining_sources(self):
        sink = MagicMock()
        sink.ingest.side_effect = SupabaseError("Unavailable")
        with (
            patch.object(api_requester, "check_source", return_value=fetch_result()),
            patch.object(api_requester.time, "sleep"),
            patch("transform_port_pegel.transform", side_effect=RuntimeError("No local HTML")),
        ):
            self.assertEqual(len(api_requester.run_cycle(sink)), len(api_requester.SOURCES))
        self.assertEqual(sink.ingest.call_count, len(api_requester.SOURCES))


class RestAndConfigTests(unittest.TestCase):
    def test_contract_columns_exist_in_unchanged_schema(self):
        schema = (Path(__file__).resolve().parent.parent / "supabase" / "schema.sql").read_text()
        for table, contract in (("fetch_runs", FetchRun), ("observations", Observation)):
            definition = re.search(rf"create table if not exists public\.{table} \((.*?)\n\);", schema, re.S)[1]
            columns = set(re.findall(r"^    (\w+) ", definition, re.M))
            self.assertTrue(set(contract.__annotations__) <= columns)

    def test_large_forecast_is_sent_in_bounded_batches(self):
        client = SupabaseRestClient("https://example.com", "example-key")
        batch = {"source": {"id": "port_pegel_forecast", "name": "Forecast", "url": "https://example.com", "kind": "html"},
                 "fetch_run": {"id": "example-run"}, "observations": [{"value": 1}] * 530}
        with patch.object(client, "request") as request:
            client.write_batch(batch)
        observation_calls = [call for call in request.call_args_list if call.args[0] == "observations"]
        self.assertEqual([len(call.args[1]) for call in observation_calls], [200, 200, 130])

    def test_secret_header_conflict_and_batches(self):
        client = SupabaseRestClient("https://example.com", "example-key")
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b""
        with patch.object(supabase_ingest, "urlopen", return_value=response) as urlopen:
            client.request("observations", [{"value": 0}], "source_id,observation_key,metric")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Apikey"), "example-key")
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(parse_qs(urlsplit(request.full_url).query)["on_conflict"],
                         ["source_id,observation_key,metric"])
        self.assertIn("merge-duplicates", request.get_header("Prefer"))

    def test_legacy_jwt_header(self):
        client = SupabaseRestClient("https://example.com", "example.jwt.value")
        self.assertEqual(client.headers["Authorization"], "Bearer example.jwt.value")

    def test_error_does_not_disclose_body_or_key(self):
        client = SupabaseRestClient("https://example.com", "example-key")
        error = HTTPError("https://example.com", 401, "example-key", {}, io.BytesIO(b"example-key"))
        with patch.object(supabase_ingest, "urlopen", side_effect=error):
            with self.assertRaises(SupabaseError) as raised:
                client.request("observations", [])
        self.assertNotIn("example-key", str(raised.exception))

    def test_dotenv_quotes_comments_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text('SUPABASE_URL="https://example.com" # comment\nSUPABASE_SECRET_KEY=example-key\n')
            with patch.object(supabase_ingest, "PROJECT_ROOT", root), patch.dict(os.environ, {"SUPABASE_URL": "https://other.example.com"}, clear=True):
                supabase_ingest.load_local_env()
                self.assertEqual(os.environ["SUPABASE_URL"], "https://other.example.com")
                self.assertEqual(os.environ["SUPABASE_SECRET_KEY"], "example-key")


if __name__ == "__main__":
    unittest.main()
