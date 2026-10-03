"""Detect supportable disturbances in saved open-data snapshots."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .config import MIN_TRAFFIC_BASELINE_SIZE, TRAFFIC_ANOMALY_THRESHOLD, TRAFFIC_FRESHNESS_MINUTES
from .logistics import traffic_volume_anomaly
from .local_data import DEFAULT_DATA_DIR, collect_local_context, read_snapshot


@dataclass(frozen=True)
class Disturbance:
    source: str
    status: Literal["detected", "no_anomaly", "unknown", "stale"]
    summary: str
    evidence: tuple[str, ...]
    action_effect: str


def _read_traffic_records(data_dir: Path) -> list[dict]:
    folder = data_dir / "basel_dataset_100006"
    records: list[dict] = []
    history = folder / "history.jsonl"
    if history.exists():
        for line in history.read_text(encoding="utf-8").splitlines():
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            records.extend((payload.get("data") or {}).get("results") or [])
    latest = read_snapshot(data_dir, "basel_dataset_100006") or {}
    records.extend((latest.get("data") or {}).get("results") or [])
    unique: dict[tuple, dict] = {}
    for record in records:
        key = (record.get("sitecode"), record.get("datetimefrom"), record.get("directionname"), record.get("lanecode"))
        if all(part is not None for part in key):
            unique[key] = record
    return list(unique.values())


def _observation_age_minutes(timestamp: str | None) -> float | None:
    if not timestamp:
        return None
    try:
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if observed.tzinfo is None or observed.utcoffset() is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds() / 60)


def detect_traffic_disturbance(data_dir: Path = DEFAULT_DATA_DIR) -> Disturbance:
    """Compare newest traffic row to older same-counter, weekday, and hour rows."""
    snapshot = read_snapshot(data_dir, "basel_dataset_100006")
    if not snapshot or not snapshot.get("request_ok"):
        return Disturbance("Basel traffic counts", "unknown", "Traffic observations are unavailable.", (),
                           "No traffic-based decision.")
    records = _read_traffic_records(data_dir)
    if not records:
        return Disturbance("Basel traffic counts", "unknown", "No usable traffic records were saved.", (),
                           "No traffic-based decision.")
    try:
        newest = max(records, key=lambda row: datetime.fromisoformat(row["datetimefrom"].replace("Z", "+00:00")))
    except (KeyError, ValueError):
        return Disturbance("Basel traffic counts", "unknown", "Traffic record timestamps are missing or invalid.", (),
                           "No traffic-based decision.")
    age = _observation_age_minutes(newest.get("datetimeto") or newest.get("datetimefrom"))
    if age is None:
        return Disturbance("Basel traffic counts", "unknown", "Traffic observation time is unknown.", (),
                           "No traffic-based decision.")
    if age > TRAFFIC_FRESHNESS_MINUTES:
        return Disturbance("Basel traffic counts", "stale",
                           f"Newest traffic observation is {age / 60:.1f} h old.",
                           ("Dataset's newest count is too old to represent current traffic.",),
                           "Do not use it to trigger a current route action.")
    group = (newest.get("sitecode"), newest.get("directionname"), newest.get("lanecode"),
             newest.get("weekday"), newest.get("hourfrom"))
    comparable = []
    for row in records:
        row_group = (row.get("sitecode"), row.get("directionname"), row.get("lanecode"),
                     row.get("weekday"), row.get("hourfrom"))
        if row_group == group and row.get("datetimefrom") != newest.get("datetimefrom") and row.get("total") is not None:
            comparable.append(float(row["total"]))
    if len(comparable) < MIN_TRAFFIC_BASELINE_SIZE:
        return Disturbance("Basel traffic counts", "unknown",
                           f"Only {len(comparable)} comparable historical counts are available; need {MIN_TRAFFIC_BASELINE_SIZE}.",
                           ("Comparison requires the same counter, direction, lane, weekday, and hour.",),
                           "No traffic-based decision.")
    anomaly = traffic_volume_anomaly(float(newest["total"]), comparable)
    if anomaly.robust_z is not None and anomaly.robust_z >= TRAFFIC_ANOMALY_THRESHOLD:
        return Disturbance("Basel traffic counts", "detected",
                           f"Unusually high traffic volume (robust z = {anomaly.robust_z:.1f}).",
                           (anomaly.reason, f"Comparable count median: {anomaly.baseline_median:g}."),
                           "Traffic volume alone does not prove congestion; use ETA/slack before changing production action.")
    return Disturbance("Basel traffic counts", "no_anomaly", "No unusually high count was detected.",
                       (anomaly.reason,), "No traffic-based decision.")


def detect_open_data_disturbances(data_dir: Path = DEFAULT_DATA_DIR) -> list[dict]:
    """Return data-supported events; environmental context is not a package excursion."""
    traffic = detect_traffic_disturbance(data_dir)
    context = collect_local_context(data_dir)
    weather = context.get("weather") or {}
    rhine = context.get("rhine") or {}
    weather_status = weather.get("source_status", "unknown")
    weather_disturbance = Disturbance(
        "MeteoSwiss weather", "unknown",
        f"Weather feed is {weather_status}; outdoor weather is handling context, not box temperature.",
        ("No calibrated weather-to-package damage threshold is configured.",),
        "No thermal decision without package telemetry or a validated scenario.",
    )
    river_status = "unknown"
    river = Disturbance(
        "Port of Switzerland Rhine gauge", river_status,
        "Current gauge is available, but no shipment ship-leg segment was supplied."
        if rhine.get("source_status") == "observed snapshot" else "Port gauge is missing or stale.",
        ("A river reading affects a shipment only on a matching ship leg.",),
        "No river-based route action without a matching ship-leg section.",
    )
    return [asdict(item) for item in (weather_disturbance, traffic, river)]
