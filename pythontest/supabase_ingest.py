"""Supabase REST ingestion with durable local retry batches; standard library only."""

import json
import os
import shlex
from datetime import timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from interfaces import FetchResult, IngestionBatch
from normalize_observations import normalize

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REQUEST_TIMEOUT = 20
OBSERVATION_BATCH_SIZE = 200


class SupabaseError(RuntimeError):
    """Only sanitized status information; never print request headers or secrets."""


def load_local_env() -> None:
    """Load plain or quoted KEY=value settings; process environment takes priority."""
    for path in (PROJECT_ROOT / ".env", PROJECT_ROOT / "pythontest" / ".env"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = shlex.split(line, comments=True)
            if parts and parts[0] == "export":
                parts = parts[1:]
            if parts and "=" in parts[0]:
                key, value = parts[0].split("=", 1)
                os.environ.setdefault(key, value)


class SupabaseRestClient:
    def __init__(self, url: str, key: str):
        if not url.startswith("https://"):
            raise SupabaseError("SUPABASE_URL must use HTTPS")
        self.url = url.rstrip("/") + "/rest/v1/"
        self.headers = {"apikey": key, "Content-Type": "application/json"}
        # New sb_secret keys are not JWTs; apikey is sufficient for them.
        if key.count(".") == 2:
            self.headers["Authorization"] = "Bearer " + key

    def request(self, table: str, rows: list[dict] | None = None,
                conflict: str | None = None, query: dict | None = None) -> object:
        params = dict(query or {})
        headers = dict(self.headers)
        if conflict:
            params["on_conflict"] = conflict
            headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
        path = self.url + table
        if params:
            path += "?" + urlencode(params)
        body = json.dumps(rows, ensure_ascii=False, allow_nan=False).encode() if rows is not None else None
        request = Request(path, data=body, headers=headers, method="POST" if rows is not None else "GET")
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                content = response.read()
                return json.loads(content) if content else None
        except HTTPError as exc:
            status = exc.code
            exc.close()
            raise SupabaseError(f"Supabase {table}: HTTP {status}") from None
        except (URLError, TimeoutError, OSError):
            raise SupabaseError(f"Supabase {table}: connection unavailable") from None

    def write_batch(self, batch: IngestionBatch) -> None:
        source = batch["source"]
        self.request("data_sources", [{
            "id": source["id"], "name": source["name"], "url": source["url"],
            "source_kind": source["kind"],
        }], "id")
        self.request("fetch_runs", [batch["fetch_run"]], "id")
        rows = batch["observations"]
        for offset in range(0, len(rows), OBSERVATION_BATCH_SIZE):
            self.request("observations", rows[offset:offset + OBSERVATION_BATCH_SIZE],
                         "source_id,observation_key,metric")


def source_last_modified(result: FetchResult) -> str | None:
    data = result.get("data")
    value = result.get("source_last_modified") or (data.get("file_last_modified") if isinstance(data, dict) else None)
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


class SupabaseIngestor:
    def __init__(self, client: SupabaseRestClient, outbox: Path):
        self.client = client
        self.outbox = outbox

    @classmethod
    def from_environment(cls):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SECRET_KEY")
        if not url and not key:
            return None
        if not url or not key:
            raise SupabaseError("Set both SUPABASE_URL and SUPABASE_SECRET_KEY")
        return cls(SupabaseRestClient(url, key), PROJECT_ROOT / ".hack" / "ingest-outbox")

    def ingest(self, source: dict, result: FetchResult) -> None:
        run_id = str(uuid4())
        normalization_error = None
        try:
            rows = normalize(result)
        except Exception as exc:
            rows = []
            normalization_error = f"{type(exc).__name__}: {exc}"
            print(f"Supabase {source['id']}: normalization FAILED — {normalization_error}", flush=True)
        for row in rows:
            row["fetch_run_id"] = run_id
        error = result.get("error")
        if normalization_error:
            error = f"{error + '; ' if error else ''}Normalization: {normalization_error}"
        batch: IngestionBatch = {
            "source": {key: source[key] for key in ("id", "name", "url", "kind")},
            "fetch_run": {
                "id": run_id, "source_id": result["source_id"], "fetched_at": result["checked_at"],
                "http_status": result.get("http_status"), "request_ok": result["request_ok"],
                "rate_limited": result.get("rate_limited", False), "retry_after": result.get("retry_after"),
                "response_bytes": result.get("response_bytes"), "error": error,
                "source_last_modified": source_last_modified(result), "raw_payload": result.get("data"),
            },
            "observations": rows, "normalization_error": normalization_error,
        }
        self.outbox.mkdir(parents=True, exist_ok=True)
        pending = self.outbox / f"{run_id}.json"
        temporary = pending.with_suffix(".tmp")
        temporary.write_text(json.dumps(batch, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temporary.replace(pending)
        self._deliver(pending, batch)

    def _deliver(self, pending: Path, batch: IngestionBatch) -> None:
        self.client.write_batch(batch)
        pending.unlink()
        print(f"Supabase {batch['source']['id']}: OK — fetch logged, {len(batch['observations'])} observations", flush=True)

    def flush(self) -> None:
        if not self.outbox.exists():
            return
        for pending in sorted(self.outbox.glob("*.json"), key=lambda path: path.stat().st_mtime):
            batch = json.loads(pending.read_text(encoding="utf-8"))
            self._deliver(pending, batch)
