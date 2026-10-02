#!/usr/bin/env python3
"""Check configured public data sources and keep a local JSON archive."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
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
        "id": "meteoswiss_station_collection",
        "name": "MeteoSwiss automatic weather stations collection",
        "url": "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-smn",
        "kind": "json",
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
