"""Read saved requester snapshots without treating them as shipment telemetry."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import LOCAL_WEATHER_FRESHNESS_MINUTES

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "pythontest" / "data"


def _age_minutes(timestamp: str | None) -> float | None:
    if not timestamp:
        return None
    try:
        observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if observed.tzinfo is None or observed.utcoffset() is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds() / 60)


def read_snapshot(data_dir: Path, source_id: str) -> dict[str, Any] | None:
    path = data_dir / source_id / "latest.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read saved snapshot {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Saved snapshot {path} must contain a JSON object")
    return value


def collect_local_context(data_dir: Path = DEFAULT_DATA_DIR) -> dict[str, Any]:
    """Summarize locally saved observations; unavailable feeds remain unknown."""
    weather_snapshot = read_snapshot(data_dir, "meteoswiss_basel_temperature")
    traffic = read_snapshot(data_dir, "basel_dataset_100006")
    rhine = read_snapshot(data_dir, "basel_dataset_100089")
    port = read_snapshot(data_dir, "port_pegel_clean")

    weather = None
    if weather_snapshot:
        station = (weather_snapshot.get("data") or {}).get("station") or {}
        checked_at = weather_snapshot.get("checked_at")
        age_minutes = _age_minutes(checked_at)
        weather = {
            "observed_at": station.get("observed_at"),
            "age_minutes_at_fetch": station.get("age_minutes_at_fetch"),
            "snapshot_age_minutes": age_minutes,
            "station_id": station.get("station_id"),
            "measurements": station.get("measurements") or {},
            "source_status": ("observed" if age_minutes is not None and age_minutes <= LOCAL_WEATHER_FRESHNESS_MINUTES else "stale")
            if weather_snapshot.get("request_ok") else "unavailable",
        }

    traffic_data = traffic.get("data", {}) if traffic else {}
    traffic_results = traffic_data.get("results") or []
    traffic_latest_age = _age_minutes(traffic_results[0].get("datetimefrom")) if traffic_results else None
    traffic_context = {
        "source_status": ("observed snapshot" if traffic_latest_age is not None and traffic_latest_age <= LOCAL_WEATHER_FRESHNESS_MINUTES else "stale")
        if traffic and traffic.get("request_ok") else "unknown",
        "latest_record_age_minutes": traffic_latest_age,
        "record_count": len(traffic_results),
        "total_count": traffic_data.get("total_count"),
        "baseline_available": False,
        "interpretation": "Counts alone do not establish congestion or travel time.",
    }

    rhine_results = (rhine or {}).get("data", {}).get("results") or []
    latest_rhine = rhine_results[0] if rhine_results else None
    port_data = port or {}
    port_current = next(
        (item for item in port_data.get("current_readings", []) if item.get("name") == "Basel-Rheinhalle"),
        None,
    )
    port_page_checked = (port or {}).get("current_page_checked_at")
    port_age = _age_minutes(port_page_checked)
    thresholds = {item.get("mark"): item for item in port_data.get("flood_thresholds", [])}
    return {
        "weather": weather,
        "traffic": traffic_context,
        "rhine": {
            "basel_stadt_latest": latest_rhine,
            "port_basel_rheinhalle": port_current,
            "port_snapshot_age_minutes": port_age,
            "port_thresholds": thresholds,
            "interpretation": "Separate gauges; apply restrictions only to a matching ship-leg segment.",
            "source_status": "observed snapshot" if port_age is not None and port_age <= LOCAL_WEATHER_FRESHNESS_MINUTES else "stale",
        },
    }
