#!/usr/bin/env python3
"""Check configured public data sources and keep a local JSON archive."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from interfaces import IngestionSink
from weather_parameters import WEATHER_PARAMETERS


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TIMEOUT_SECONDS = 30
RHINE_RECORD_LIMIT = 48
RAW_KEEP = 50

SOURCES = [
    {
        "id": "meteoswiss_basel_temperature",
        "name": "MeteoSwiss Basel/Binningen temperature",
        "url": "https://data.geo.admin.ch/ch.meteoschweiz.messwerte-aktuell/VQHA80.csv",
        "kind": "meteo_current",
        "station_id": "BAS",
    },
    {
        "id": "basel_dataset_100006",
        "name": "Basel-Stadt dataset 100006 records",
        "url": "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100006/records/?lang=en&limit=10&offset=0&order_by=-datetimefrom",
        "kind": "json",
        "basel_auth": True,
    },
    {
        "id": "basel_dataset_100089",
        "name": "Basel-Stadt dataset 100089 records",
        "url": "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089/records/",
        "params": {"lang": "en", "limit": RHINE_RECORD_LIMIT, "offset": 0, "order_by": "-timestamp"},
        "kind": "json",
        "basel_auth": True,
    },
    {
        "id": "opentransportdata_basel_region",
        "name": "OpenTransportData Basel-region road traffic",
        "url": "https://api.opentransportdata.swiss/TDP/Soap_Datex2/TrafficSituations/Pull",
        "kind": "opentransportdata",
    },
    {
        "id": "port_pegel_current",
        "name": "Port of Switzerland water levels",
        "url": "https://port-of-switzerland.ch/hafenservice/pegel/",
        "kind": "html",
    },
    {
        "id": "port_pegel_forecast",
        "name": "Port of Switzerland water-level forecast table (BAFU data)",
        "url": "https://port-of-switzerland.ch/hafenservice/pegel/vorhersage-tabelle/",
        "kind": "html",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PageExtractor(HTMLParser):
    """Extract visible text, headings, and tables without third-party packages."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.headings: list[str] = []
        self.tables: list[list[list[str]]] = []
        self._heading_level = 0
        self._heading_text = ""
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("h1", "h2", "h3", "h4"):
            self._heading_level = int(tag[1])
            self._heading_text = ""
        elif tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("h1", "h2", "h3", "h4") and self._heading_level:
            title = clean_text(self._heading_text)
            if title:
                self.headings.append(title)
            self._heading_level = 0
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(clean_text("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if any(self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text_parts.append(data.strip())
        if self._heading_level:
            self._heading_text += data
        if self._cell is not None:
            self._cell.append(data)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def source_url(source: dict) -> str:
    params = source.get("params")
    if not params:
        return source["url"]
    separator = "&" if "?" in source["url"] else "?"
    return source["url"] + separator + urlencode(params)


def read_response(source: dict) -> tuple[int | None, dict, bytes | None, str | None]:
    headers = {"User-Agent": "api-requester/1.0 (local data monitoring)"}
    api_key = os.environ.get("API_KEY")
    if source.get("basel_auth") and api_key:
        headers["Authorization"] = f"Apikey {api_key}"
    request = Request(source_url(source), headers=headers, method="GET")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, dict(response.headers.items()), response.read(), None
    except HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read(), str(exc)
    except (URLError, TimeoutError, OSError) as exc:
        return None, {}, None, str(exc)


def parse_payload(source: dict, body: bytes | None) -> tuple[object, str | None]:
    if body is None:
        return None, None
    text = body.decode("utf-8", errors="replace")
    if source["kind"] == "json":
        try:
            return json.loads(text), None
        except json.JSONDecodeError as exc:
            return {"body_text": text}, f"Response was not valid JSON: {exc}"
    parser = PageExtractor()
    try:
        parser.feed(text)
        parser.close()
        return {
            "page_title_and_headings": parser.headings,
            "tables": parser.tables,
            "text": clean_text(" ".join(parser.text_parts)),
            "raw_html_file": None,
        }, None
    except Exception as exc:  # Keep the raw page even if extraction changes unexpectedly.
        return {"body_text": text}, f"HTML extraction failed: {exc}"


def prune_raw_files(raw_dir: Path, latest_raw_path: Path) -> None:
    files = sorted((path for path in raw_dir.glob("*.html") if path.is_file()), key=lambda path: path.name, reverse=True)
    # Reserve a slot for latest.json even if the system clock moved backwards.
    keep = {latest_raw_path}
    keep.update([path for path in files if path != latest_raw_path][:RAW_KEEP - 1])
    for path in files:
        if path not in keep:
            path.unlink()


def save_result(source: dict, result: dict, body: bytes | None) -> None:
    folder = DATA_DIR / source["id"]
    folder.mkdir(parents=True, exist_ok=True)
    raw_path = None
    if result["request_ok"]:
        if body is not None and source["kind"] == "html":
            raw_dir = folder / "raw"
            raw_dir.mkdir(exist_ok=True)
            raw_path = raw_dir / (result["checked_at"].replace(":", "-") + ".html")
            raw_path.write_bytes(body)
            result["data"]["raw_html_file"] = str(raw_path.relative_to(ROOT))
        result_path = folder / "latest.json"
    else:
        result_path = folder / "last_error.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (folder / "history.jsonl").open("a", encoding="utf-8") as history:
        history.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    if raw_path is not None:
        prune_raw_files(raw_path.parent, raw_path)


def check_source(source: dict) -> dict:
    if source["kind"] == "meteo_current":
        return check_meteoswiss_current(source)
    if source["kind"] == "opentransportdata":
        return check_opentransportdata(source)
    checked_at = now_utc()
    status, headers, body, transport_error = read_response(source)
    payload, parse_error = parse_payload(source, body)
    rate_limited = status == 429
    ok = status is not None and 200 <= status < 300 and parse_error is None
    result = {
        "source_id": source["id"],
        "name": source["name"],
        "url": source_url(source),
        "checked_at": checked_at,
        "http_status": status,
        "request_ok": ok,
        "rate_limited": rate_limited,
        "retry_after": headers.get("Retry-After") or headers.get("retry-after"),
        "response_bytes": len(body) if body is not None else None,
        "source_last_modified": headers.get("Last-Modified") or headers.get("last-modified"),
        "error": transport_error or parse_error,
        "data": payload,
    }
    result["saved"] = True
    result["latest_file"] = str((DATA_DIR / source["id"] / "latest.json").relative_to(ROOT))
    result["history_file"] = str((DATA_DIR / source["id"] / "history.jsonl").relative_to(ROOT))
    save_error = None
    try:
        save_result(source, result, body)
    except OSError as exc:
        save_error = str(exc)
        result["saved"] = False
        result["save_error"] = save_error
        # If the first write succeeded but a later archive write failed, keep
        # the latest status honest whenever the filesystem still permits it.
        if result["request_ok"]:
            try:
                latest_path = DATA_DIR / source["id"] / "latest.json"
                latest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except OSError:
                pass
    label = source["name"]
    if rate_limited:
        outcome = f"FAILED — rate limited (HTTP 429; Retry-After: {result['retry_after'] or 'not provided'})"
    elif save_error:
        outcome = f"FAILED — could not save response (HTTP {status})"
    elif ok:
        outcome = f"OK — HTTP {status}"
    elif status is not None:
        outcome = f"FAILED — HTTP {status}"
    else:
        outcome = "FAILED — connection error"
    print(f"{label}: {outcome}", flush=True)
    return result


def check_opentransportdata(source: dict, snapshot: dict | None = None) -> dict:
    """Collect and archive the OTD situation and counter feeds as one source."""
    checked_at = now_utc()
    data = None
    error = None
    try:
        import opentransportdata

        data = snapshot if snapshot is not None else opentransportdata.fetch_all()
        if data["errors"]:
            error = "; ".join(data["errors"])
        # Preserve the dedicated per-minute counter archive as well as this
        # collector's normal per-source attempt history.
        if snapshot is None:
            opentransportdata.save_snapshot(data)
    except (OSError, RuntimeError, ValueError) as exc:
        error = f"{type(exc).__name__}: {exc}"

    status_codes = re.findall(r"\bHTTP (\d{3})\b", error or "")
    http_status = int(status_codes[-1]) if status_codes else (200 if data is not None and not error else None)
    ok = data is not None and not error
    result = {
        "source_id": source["id"], "name": source["name"], "url": source["url"],
        "checked_at": checked_at, "http_status": http_status,
        "request_ok": ok, "rate_limited": http_status == 429, "retry_after": None,
        "response_bytes": None, "error": error, "saved": True,
        "latest_file": str((DATA_DIR / source["id"] / "latest.json").relative_to(ROOT)),
        "history_file": str((DATA_DIR / source["id"] / "history.jsonl").relative_to(ROOT)),
        "data": data,
    }
    try:
        save_result(source, result, None)
    except OSError as exc:
        result["saved"] = False
        result["save_error"] = str(exc)

    counts = data or {}
    counter_data = counts.get("traffic_counters", {})
    if not result["saved"]:
        status = "FAILED — could not save response"
    elif ok:
        status = (f"OK — {len(counts.get('traffic_situations', []))} situations, "
                  f"{len(counter_data.get('sites', []))} counter sites, "
                  f"{len(counter_data.get('current_readings', []))} current readings")
    else:
        status = f"FAILED — {error or 'request failed'}"
    print(f"{source['name']}: {status}", flush=True)
    return result


def parse_csv_value(value: str) -> object:
    value = value.strip()
    if not value:
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def check_meteoswiss_current(source: dict) -> dict:
    checked_at = now_utc()
    status, headers, body, transport_error = read_response(source)
    error = transport_error
    station: dict = {"station_id": source["station_id"], "station_name": "Basel / Binningen"}
    parameter_metadata: dict = {}
    if body is not None and status is not None and 200 <= status < 300:
        try:
            text = body.decode("cp1252")
            rows = csv.DictReader(io.StringIO(text, newline=""), delimiter=";")
            row = next((r for r in rows if r.get("Station/Location", "").strip().upper() == source["station_id"]), None)
            if row is None:
                raise ValueError(f"Station {source['station_id']} not present in current-values CSV")
            observed_utc = datetime.strptime(row["Date"].strip(), "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
            observed_local = observed_utc.astimezone(ZoneInfo("Europe/Zurich"))
            measurements = {}
            for metric in WEATHER_PARAMETERS:
                value = parse_csv_value(row.get(metric, ""))
                measurements[metric] = value if isinstance(value, (int, float)) and math.isfinite(value) else None
            if not any(value is not None for value in measurements.values()):
                raise ValueError("No valid current weather measurements for BAS")
            station.update({
                "observed_at_utc": observed_utc.isoformat().replace("+00:00", "Z"),
                "observed_at": observed_local.isoformat(timespec="minutes"),
                "time_zone": "Europe/Zurich",
                "age_minutes_at_fetch": round((datetime.now(timezone.utc) - observed_utc).total_seconds() / 60, 1),
                "measurements": measurements,
                "missing_measurements": [metric for metric, value in measurements.items() if value is None],
            })
            parameter_metadata = {metric: dict(metadata) for metric, metadata in WEATHER_PARAMETERS.items()}
        except (UnicodeError, csv.Error, KeyError, ValueError) as exc:
            error = f"Could not parse MeteoSwiss current-values CSV: {exc}"
    rate_limited = status == 429
    ok = status is not None and 200 <= status < 300 and error is None
    result = {
        "source_id": source["id"],
        "name": source["name"],
        "url": source["url"],
        "checked_at": checked_at,
        "http_status": status,
        "request_ok": ok,
        "rate_limited": rate_limited,
        "retry_after": headers.get("Retry-After") or headers.get("retry-after"),
        "response_bytes": len(body) if body is not None else None,
        "error": error,
        "saved": True,
        "latest_file": str((DATA_DIR / source["id"] / "latest.json").relative_to(ROOT)),
        "history_file": str((DATA_DIR / source["id"] / "history.jsonl").relative_to(ROOT)),
        "data": {
            "dataset": "MeteoSwiss current measurements, all stations",
            "station": station if "measurements" in station else None,
            "parameter_metadata": parameter_metadata,
            "file_last_modified": headers.get("Last-Modified"),
        },
    }
    try:
        save_result(source, result, None)
    except OSError as exc:
        result["saved"] = False
        result["save_error"] = str(exc)
    if rate_limited:
        status_line = f"FAILED — rate limited (HTTP 429; Retry-After: {result['retry_after'] or 'not provided'})"
    elif not result["saved"]:
        status_line = "FAILED — could not save response"
    elif result["request_ok"]:
        temp = station["measurements"]["tre200s0"]
        if temp is not None:
            status_line = f"OK — HTTP {status} — {temp} °C at {station['observed_at']} ({station['age_minutes_at_fetch']} min old; Europe/Zurich)"
        else:
            count = sum(value is not None for value in station["measurements"].values())
            status_line = f"OK — HTTP {status} — {count} weather values at {station['observed_at']} (temperature unavailable; Europe/Zurich)"
    else:
        status_line = f"FAILED — HTTP {status or 'connection error'} — {error}"
    print(f"{source['name']}: {status_line}", flush=True)
    return result


def create_ingestor(local_only: bool = False) -> IngestionSink | None:
    if local_only:
        return None
    from supabase_ingest import SupabaseIngestor, load_local_env

    load_local_env()
    ingestor = SupabaseIngestor.from_environment()
    if ingestor is None:
        print("Supabase disabled — set SUPABASE_URL and SUPABASE_SECRET_KEY in .env", flush=True)
    return ingestor


def run_cycle(ingestor: IngestionSink | None = None) -> list[dict]:
    print(f"\nChecking {len(SOURCES)} sources ({now_utc()})", flush=True)
    if ingestor is not None:
        try:
            ingestor.flush()
        except Exception as exc:
            print(f"Supabase retry: FAILED — {type(exc).__name__}: {exc}", flush=True)
    results = []
    for source in SOURCES:
        try:
            result = check_source(source)
            results.append(result)
        except Exception as exc:
            print(f"{source['name']}: FAILED — {type(exc).__name__}: {exc}", flush=True)
            result = {
                "source_id": source["id"], "checked_at": now_utc(), "http_status": None,
                "request_ok": False, "rate_limited": False, "retry_after": None,
                "response_bytes": None, "error": f"{type(exc).__name__}: {exc}", "data": None,
            }
        if ingestor is not None:
            try:
                ingestor.ingest(source, result)
            except Exception as exc:
                print(f"Supabase {source['id']}: FAILED — {type(exc).__name__}: {exc}; local archives retained", flush=True)
        time.sleep(0.5)
    try:
        from transform_port_pegel import save, transform

        clean_data = transform()
        saved_path = save(clean_data)
        print(f"Clean port data saved: {saved_path.relative_to(ROOT)}", flush=True)
    except ModuleNotFoundError as exc:
        if exc.name == "transform_port_pegel":
            print(
                "Clean port data: SKIPPED — transform_port_pegel.py is missing; "
                "source responses remain saved in data/.",
                flush=True,
            )
        else:
            print(f"Clean port data: FAILED — {type(exc).__name__}: {exc}", flush=True)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"Clean port data: FAILED — {exc}", flush=True)
    except Exception as exc:
        print(f"Clean port data: FAILED — {type(exc).__name__}: {exc}", flush=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    parser.add_argument("--local-only", action="store_true", help="keep local archives without writing to Supabase")
    parser.add_argument("--interval", type=int, default=600, help="seconds between cycles in watch mode (default: 600)")
    args = parser.parse_args()
    if args.interval < 1:
        parser.error("--interval must be at least 1 second")
    try:
        try:
            ingestor = create_ingestor(args.local_only)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"Supabase disabled — {exc}; local collection continues", flush=True)
            ingestor = None
        if args.once:
            run_cycle(ingestor)
            return 0
        print(f"Watching every {args.interval} seconds. Press Ctrl+C to stop.")
        while True:
            try:
                run_cycle(ingestor)
            except Exception as exc:
                print(f"Cycle: FAILED — {type(exc).__name__}: {exc}", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
