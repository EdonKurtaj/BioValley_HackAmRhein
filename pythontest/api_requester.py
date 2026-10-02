#!/usr/bin/env python3
"""Check configured public data sources and keep a local JSON archive."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
TIMEOUT_SECONDS = 30

SOURCES = [
    {
        "id": "meteoswiss_basel_temperature",
        "name": "MeteoSwiss Basel/Binningen temperature",
        "url": "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn/items/bas",
        "kind": "meteo_current",
        "station_ids": ["bas"],
        "measurement_parameters": ["tre200s0"],
    },
    {
        "id": "basel_dataset_100006",
        "name": "Basel-Stadt dataset 100006 records",
        "url": "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100006/records/?lang=en&limit=10&offset=0",
        "kind": "json",
        "basel_auth": True,
    },
    {
        "id": "basel_dataset_100089",
        "name": "Basel-Stadt dataset 100089 records",
        "url": "https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089/records/?lang=en&limit=10&offset=0",
        "kind": "json",
        "basel_auth": True,
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


def read_response(source: dict) -> tuple[int | None, dict, bytes | None, str | None]:
    headers = {"User-Agent": "api-requester/1.0 (local data monitoring)"}
    api_key = os.environ.get("API_KEY")
    if source.get("basel_auth") and api_key:
        headers["Authorization"] = f"Apikey {api_key}"
    request = Request(source["url"], headers=headers, method="GET")
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


def save_result(source: dict, result: dict, body: bytes | None) -> None:
    folder = DATA_DIR / source["id"]
    folder.mkdir(parents=True, exist_ok=True)
    if body is not None and source["kind"] == "html":
        raw_dir = folder / "raw"
        raw_dir.mkdir(exist_ok=True)
        raw_path = raw_dir / (result["checked_at"].replace(":", "-") + ".html")
        raw_path.write_bytes(body)
        result["data"]["raw_html_file"] = str(raw_path.relative_to(ROOT))
    (folder / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (folder / "history.jsonl").open("a", encoding="utf-8") as history:
        history.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")


def check_source(source: dict) -> dict:
    if source["kind"] == "meteo_current":
        return check_meteoswiss_current(source)
    checked_at = now_utc()
    status, headers, body, transport_error = read_response(source)
    payload, parse_error = parse_payload(source, body)
    rate_limited = status == 429
    ok = status is not None and 200 <= status < 300 and parse_error is None
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


METEO_PARAMETER_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/ogd-smn_meta_parameters.csv"


def parse_csv_value(value: str) -> object:
    value = value.strip()
    if not value:
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def fetch_station_current(station: dict) -> tuple[dict, bytes | None, str | None, int | None, str | None]:
    asset = next(
        (asset for key, asset in station.get("assets", {}).items() if key.endswith("_t_now.csv")),
        None,
    )
    station_info = {
        "station_id": station.get("id"),
        "name": station.get("properties", {}).get("title"),
        "coordinates_lon_lat": station.get("geometry", {}).get("coordinates"),
    }
    if not asset:
        return station_info, None, "No ten-minute current-data CSV available", None, None
    response = Request(asset["href"], headers={"User-Agent": "api-requester/1.0 (local data monitoring)"})
    try:
        with urlopen(response, timeout=TIMEOUT_SECONDS) as answer:
            body = answer.read()
            rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig", errors="replace")), delimiter=";"))
            if not rows:
                raise ValueError("CSV has no measurement rows")
            timestamp_column = "reference_timestamp"
            def timestamp_key(row: dict) -> datetime:
                return datetime.strptime(row[timestamp_column], "%d.%m.%Y %H:%M")
            latest_row = max(rows, key=timestamp_key)
            timestamp = latest_row.pop(timestamp_column, None)
            abbreviation = latest_row.pop("station_abbr", None)
            station_info["station_abbr"] = abbreviation
            station_info["observed_at"] = timestamp
            wanted = station.get("measurement_parameters")
            station_info["measurements"] = {
                key: parse_csv_value(value)
                for key, value in latest_row.items()
                if not wanted or key in wanted
            }
            station_info["measurement_count"] = sum(value is not None for value in station_info["measurements"].values())
            return station_info, body, None, answer.status, answer.headers.get("Retry-After")
    except HTTPError as exc:
        return station_info, None, str(exc), exc.code, exc.headers.get("Retry-After")
    except (URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
        return station_info, None, str(exc), None, None


def load_meteo_parameter_metadata() -> dict:
    """Cache the official parameter dictionary locally and map CSV codes to names/units."""
    folder = DATA_DIR / "meteoswiss_basel_temperature"
    cache_path = folder / "parameter_metadata.csv"
    if not cache_path.exists():
        request = Request(METEO_PARAMETER_URL, headers={"User-Agent": "api-requester/1.0 (local data monitoring)"})
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(response.read())
    raw = cache_path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    rows = csv.DictReader(io.StringIO(text), delimiter=";")
    return {
        row["parameter_shortname"]: {
            "name_de": row.get("parameter_description_de", ""),
            "name_en": row.get("parameter_description_en", ""),
            "unit": row.get("parameter_unit", ""),
            "group": row.get("parameter_group_de", ""),
        }
        for row in rows
        if row.get("parameter_shortname")
    }


def check_meteoswiss_current(source: dict) -> dict:
    checked_at = now_utc()
    print(f"{source['name']}: Abruf läuft ...", flush=True)
    items: list[dict] = []
    page_url: str | None = source["url"]
    listing_status: int | None = None
    listing_error: str | None = None
    listing_bytes = 0
    retry_after = None
    while page_url:
        status, headers, body, error = read_response({**source, "url": page_url})
        listing_status = status
        listing_bytes += len(body or b"")
        if status != 200 or body is None:
            listing_error = error or f"Station item list returned HTTP {status}"
            retry_after = headers.get("Retry-After") or headers.get("retry-after")
            break
        try:
            page = json.loads(body)
        except json.JSONDecodeError as exc:
            listing_error = f"Station item list was not valid JSON: {exc}"
            break
        if page.get("type") == "FeatureCollection":
            items.extend(page.get("features", []))
            page_url = next((link.get("href") for link in page.get("links", []) if link.get("rel") == "next"), None)
        elif page.get("type") == "Feature":
            items.append(page)
            page_url = None
        else:
            listing_error = "Station item response is not a STAC Feature or FeatureCollection"
            page_url = None

    wanted_stations = set(source.get("station_ids", []))
    if wanted_stations:
        items = [item for item in items if item.get("id", "").lower() in wanted_stations]
    for item in items:
        item["measurement_parameters"] = source.get("measurement_parameters", [])

    measurements: list[dict] = []
    station_errors: list[dict] = []
    parameter_metadata: dict = {}
    total_bytes = listing_bytes
    rate_limited = listing_status == 429
    subrequest_statuses: list[int] = []
    if not listing_error:
        try:
            parameter_metadata = load_meteo_parameter_metadata()
        except (HTTPError, URLError, TimeoutError, OSError, csv.Error) as exc:
            # Values are still useful under their official short parameter codes.
            station_errors.append({"resource": "parameter metadata", "error": str(exc)})
        with ThreadPoolExecutor(max_workers=6) as executor:
            fetched = list(executor.map(fetch_station_current, items))
        for station_result, body, error, status, retry in fetched:
            total_bytes += len(body or b"")
            if status is not None:
                subrequest_statuses.append(status)
            if status == 429:
                rate_limited = True
                retry_after = retry_after or retry
            if error:
                station_errors.append({"station_id": station_result.get("station_id"), "name": station_result.get("name"), "http_status": status, "error": error})
            else:
                measurements.append(station_result)

    used_parameters = sorted({key for station in measurements for key in station.get("measurements", {})})
    result = {
        "source_id": source["id"],
        "name": source["name"],
        "url": source["url"],
        "checked_at": checked_at,
        "http_status": listing_status,
        "request_ok": not listing_error and bool(measurements) and not station_errors,
        "rate_limited": rate_limited,
        "retry_after": retry_after,
        "response_bytes": total_bytes,
        "error": listing_error,
        "saved": True,
        "latest_file": str((DATA_DIR / source["id"] / "latest.json").relative_to(ROOT)),
        "history_file": str((DATA_DIR / source["id"] / "history.jsonl").relative_to(ROOT)),
        "data": {
            "collection_id": "ch.meteoschweiz.ogd-smn",
            "station_count": len(items),
            "stations_with_current_data": len(measurements),
            "stations": measurements,
            "parameter_metadata": {key: parameter_metadata[key] for key in used_parameters if key in parameter_metadata},
            "parameter_codes_without_metadata": [key for key in used_parameters if key not in parameter_metadata],
            "station_errors": station_errors,
        },
    }
    try:
        save_result(source, result, None)
    except OSError as exc:
        result["saved"] = False
        result["save_error"] = str(exc)
    if rate_limited:
        status_line = f"FAILED — rate limited (HTTP 429; Retry-After: {retry_after or 'not provided'})"
    elif not result["saved"]:
        status_line = "FAILED — could not save response"
    elif result["request_ok"]:
        bas_temperature = next(
            (station for station in measurements if station.get("station_id", "").lower() == "bas"),
            None,
        )
        temp = bas_temperature.get("measurements", {}).get("tre200s0") if bas_temperature else None
        observed_at = bas_temperature.get("observed_at") if bas_temperature else None
        status_line = f"OK — HTTP 200 — {temp} °C at {observed_at}"
    elif listing_error:
        status_line = f"FAILED — HTTP {listing_status or 'connection error'}"
    else:
        status_line = f"FAILED — data missing for {len(station_errors)} resource(s)"
    print(f"{source['name']}: {status_line}", flush=True)
    return result


def run_cycle() -> list[dict]:
    print(f"\nChecking {len(SOURCES)} sources ({now_utc()})", flush=True)
    results = []
    for source in SOURCES:
        results.append(check_source(source))
        time.sleep(0.5)
    try:
        from transform_port_pegel import save, transform

        clean_data = transform()
        saved_path = save(clean_data)
        print(f"Clean port data saved: {saved_path.relative_to(ROOT)}", flush=True)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"Clean port data: FAILED — {exc}", flush=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    parser.add_argument("--interval", type=int, default=600, help="seconds between cycles in watch mode (default: 600)")
    args = parser.parse_args()
    if args.interval < 1:
        parser.error("--interval must be at least 1 second")
    try:
        if args.once:
            run_cycle()
            return 0
        print(f"Watching every {args.interval} seconds. Press Ctrl+C to stop.")
        while True:
            run_cycle()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
