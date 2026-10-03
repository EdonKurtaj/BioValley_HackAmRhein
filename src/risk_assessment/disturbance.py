"""Detect supportable disturbances in saved open-data snapshots."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from typing import Literal

from .config import (
    COLD_AMBIENT_MAX_C,
    COLD_AMBIENT_ONSET_C,
    HEAVY_RAIN_MAX_MM_10MIN,
    HEAVY_RAIN_ONSET_MM_10MIN,
    HOT_AMBIENT_MAX_C,
    HOT_AMBIENT_ONSET_C,
    MIN_TRAFFIC_BASELINE_SIZE,
    STRONG_GUST_MAX_KMH,
    STRONG_GUST_ONSET_KMH,
    TRAFFIC_ANOMALY_THRESHOLD,
    TRAFFIC_FRESHNESS_MINUTES,
)
from .logistics import traffic_volume_anomaly
from .local_data import DEFAULT_DATA_DIR, collect_local_context, read_snapshot


@dataclass(frozen=True)
class Disturbance:
    source: str
    status: Literal["detected", "no_anomaly", "unknown", "stale"]
    summary: str
    evidence: tuple[str, ...]
    action_effect: str
    robust_z: float | None = None


def _ramp_up(value: float, onset: float, maximum: float) -> float:
    return min(100.0, max(0.0, (value - onset) / (maximum - onset) * 100.0))


def _ramp_down(value: float, onset: float, maximum: float) -> float:
    return min(100.0, max(0.0, (onset - value) / (onset - maximum) * 100.0))


def score_weather_context(measurements: dict) -> dict:
    """Scale current outdoor extremes into a bounded handling-context signal."""
    required = {"temperature_c": "tre200s0", "precipitation_mm_10min": "rre150z0",
                "gust_kmh": "fu3010z1"}
    values = {name: measurements.get(field) for name, field in required.items()}
    if any(value is None for value in values.values()):
        return {"status": "unknown", "score": None, "measurements": values,
                "subscores": {}, "evidence": ["One or more weather fields used by the context score are missing."]}
    try:
        temperature, precipitation, gust = (float(values[key]) for key in required)
    except (TypeError, ValueError):
        return {"status": "unknown", "score": None, "measurements": values,
                "subscores": {}, "evidence": ["A weather field used by the context score is not numeric."]}
    if not all(isfinite(value) for value in (temperature, precipitation, gust)) or precipitation < 0 or gust < 0:
        return {"status": "unknown", "score": None, "measurements": values,
                "subscores": {}, "evidence": ["A weather field used by the context score is invalid."]}

    subscores = {
        "hot_ambient": _ramp_up(temperature, HOT_AMBIENT_ONSET_C, HOT_AMBIENT_MAX_C),
        "cold_ambient": _ramp_down(temperature, COLD_AMBIENT_ONSET_C, COLD_AMBIENT_MAX_C),
        "precipitation": _ramp_up(precipitation, HEAVY_RAIN_ONSET_MM_10MIN, HEAVY_RAIN_MAX_MM_10MIN),
        "wind_gust": _ramp_up(gust, STRONG_GUST_ONSET_KMH, STRONG_GUST_MAX_KMH),
    }
    score = max(subscores.values())
    triggers = [name.replace("_", " ") for name, value in subscores.items() if value > 0]
    return {
        "status": "detected" if score > 0 else "no_anomaly",
        "score": round(score, 1),
        "measurements": values,
        "subscores": {name: round(value, 1) for name, value in subscores.items()},
        "evidence": [f"Elevated weather context: {', '.join(triggers)}."] if triggers
        else ["No configured hot, cold, heavy-rain, or strong-gust context trigger."],
    }


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
                           "Traffic volume alone does not prove congestion; use ETA/slack before changing production action.",
                           anomaly.robust_z)
    return Disturbance("Basel traffic counts", "no_anomaly", "No unusually high count was detected.",
                       (anomaly.reason,), "No traffic-based decision.", anomaly.robust_z)


def detect_open_data_disturbances(data_dir: Path = DEFAULT_DATA_DIR) -> list[dict]:
    """Return data-supported events; environmental context is not a package excursion."""
    traffic = detect_traffic_disturbance(data_dir)
    context = collect_local_context(data_dir)
    weather = context.get("weather") or {}
    rhine = context.get("rhine") or {}
    weather_status = weather.get("source_status", "unknown")
    weather_context = score_weather_context(weather.get("measurements") or {})
    if weather_status != "observed":
        weather_context["status"] = weather_status if weather_status in ("stale", "unavailable") else "unknown"
        weather_context["score"] = None
        weather_context["evidence"] = [f"Weather feed is {weather_status}; no current weather score is available."]
    weather_disturbance = Disturbance(
        "MeteoSwiss weather", weather_context["status"],
        f"Outdoor weather context score: {weather_context['score'] if weather_context['score'] is not None else 'unknown'}/100; this is not box temperature.",
        tuple(weather_context["evidence"]),
        "Handling context only; no package excursion can be inferred from station weather.",
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
