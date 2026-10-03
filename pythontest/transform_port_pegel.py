#!/usr/bin/env python3
"""Turn the saved Port of Switzerland Pegel pages into compact structured JSON."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from api_requester import DATA_DIR, PageExtractor

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = DATA_DIR / "port_pegel_clean"


class VisiblePageExtractor(PageExtractor):
    """Reuse the table parser but ignore HTML head, scripts, styles, and noscript."""

    def __init__(self) -> None:
        super().__init__()
        self._skip_tag: str | None = None

    def handle_starttag(self, tag, attrs):
        if self._skip_tag:
            return
        if tag in {"head", "script", "style", "noscript"}:
            self._skip_tag = tag
            return
        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if self._skip_tag:
            if tag == self._skip_tag:
                self._skip_tag = None
            return
        super().handle_endtag(tag)

    def handle_data(self, data):
        if not self._skip_tag:
            super().handle_data(data)


def latest_page(source_id: str) -> tuple[dict, str]:
    latest_path = DATA_DIR / source_id / "latest.json"
    record = json.loads(latest_path.read_text(encoding="utf-8"))
    raw_relative = record.get("data", {}).get("raw_html_file")
    if not raw_relative:
        raise RuntimeError(f"No saved HTML path in {latest_path}; run the API checker first.")
    raw_path = ROOT / raw_relative
    return record, raw_path.read_text(encoding="utf-8", errors="replace")


def page_tables(html: str) -> tuple[list[list[list[str]]], str]:
    parser = VisiblePageExtractor()
    parser.feed(html)
    parser.close()
    return parser.tables, " ".join(parser.text_parts)


def number_and_unit(text: str) -> tuple[int | float, str]:
    match = re.fullmatch(r"\s*([+-]?\d+(?:[.,]\d+)?)\s*(.*?)\s*", text)
    if not match:
        raise ValueError(f"Could not parse measurement: {text!r}")
    raw_number, unit = match.groups()
    value = float(raw_number.replace(",", "."))
    if value.is_integer():
        value = int(value)
    return value, unit


def parse_current(tables: list[list[list[str]]]) -> tuple[list[dict], list[dict]]:
    readings: list[dict] = []
    thresholds: list[dict] = []
    for table in tables:
        if not table:
            continue
        headers = [header.casefold() for header in table[0]]
        if "gewässer/see" in headers and "aktueller wert" in headers:
            for row in table[1:]:
                if len(row) < 3:
                    continue
                value, unit = number_and_unit(row[1])
                readings.append({"name": row[0], "value": value, "unit": unit, "observed_at": row[2]})
        elif "hochwassermarke" in headers and "abflussmenge basel-rheinhalle" in headers:
            for row in table[1:]:
                if len(row) < 3:
                    continue
                water_level, level_unit = number_and_unit(row[1])
                discharge_match = re.fullmatch(r"\s*(?:ca\.?\s*)?([\d.,]+)\s*(.*?)\s*", row[2])
                if not discharge_match:
                    raise ValueError(f"Could not parse flood discharge: {row[2]!r}")
                discharge_value = float(discharge_match.group(1).replace(",", "."))
                if discharge_value.is_integer():
                    discharge_value = int(discharge_value)
                thresholds.append({
                    "mark": row[0],
                    "water_level": water_level,
                    "water_level_unit": level_unit,
                    "discharge_approx": discharge_value,
                    "discharge_unit": discharge_match.group(2),
                })
    if not readings:
        raise RuntimeError("Could not find the current water-level table in the saved HTML.")
    return readings, thresholds


def matched_text(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def parse_forecast(tables: list[list[list[str]]], text: str) -> dict:
    forecast_table = next(
        (table for table in tables if table and "datum - zeit" in [value.casefold() for value in table[0]]),
        None,
    )
    if forecast_table is None:
        raise RuntimeError("Could not find the forecast table in the saved HTML.")

    rows = []
    for row in forecast_table[1:]:
        if len(row) < 3:
            continue
        rows.append({
            "time": row[0],
            "water_level_m_above_sea_level": float(row[1].replace(",", ".")),
            "discharge_m3_per_second": float(row[2].replace(",", ".")),
        })
    return {
        "issued_at": matched_text(text, r"Ausgegeben am\s*/\s*Emission:\s*(.*?)\s*Meteolauf von"),
        "weather_model_run_at": matched_text(text, r"Meteolauf von\s*/\s*Prévision météo de:\s*(.*?)\s*Gemessene Werte bis"),
        "measured_values_until": matched_text(text, r"Gemessene Werte bis\s*/\s*Valeurs mesurées jusqu'au:\s*(.*?)\s*Übrige Zeitangaben in"),
        "time_zone": matched_text(text, r"Übrige Zeitangaben in\s*/\s*Autres valeurs de temps en\s*:\s*(.*?)\s*Stundenmittel des Wasserstandes"),
        "rows": rows,
    }


def transform() -> dict:
    current_record, current_html = latest_page("port_pegel_current")
    forecast_record, forecast_html = latest_page("port_pegel_forecast")
    current_tables, _ = page_tables(current_html)
    forecast_tables, forecast_text = page_tables(forecast_html)
    readings, thresholds = parse_current(current_tables)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current_page_checked_at": current_record["checked_at"],
        "forecast_page_checked_at": forecast_record["checked_at"],
        "current_readings": readings,
        "flood_thresholds": thresholds,
        "forecast": parse_forecast(forecast_tables, forecast_text),
    }


def save(data: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    latest_path = OUTPUT_DIR / "latest.json"
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    latest_path.write_text(serialized, encoding="utf-8")
    with (OUTPUT_DIR / "history.jsonl").open("a", encoding="utf-8") as history:
        history.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    return latest_path


def main() -> int:
    try:
        data = transform()
        path = save(data)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print(f"Port Pegel transform failed: {exc}")
        return 1
    print(f"Clean Port Pegel data saved to {path.relative_to(ROOT)}")
    print(f"Current readings: {len(data['current_readings'])}; flood marks: {len(data['flood_thresholds'])}; forecast hours: {len(data['forecast']['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
