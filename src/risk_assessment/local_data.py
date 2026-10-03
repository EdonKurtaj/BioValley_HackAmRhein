"""Read saved requester snapshots without treating them as shipment telemetry."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import LOCAL_WEATHER_FRESHNESS_MINUTES, PORT_GAUGE_FRESHNESS_MINUTES, TRAFFIC_FRESHNESS_MINUTES

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "pythontest" / "data"


def _port_observation_time(value: object) -> datetime | None:
    """Read aware ISO times or the Port page's Europe/Zurich local timestamp.

    Ambiguous or nonexistent daylight-saving wall times remain unknown.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%d.%m.%Y %H:%M")
        except ValueError:
            return None
        zone = ZoneInfo("Europe/Zurich")
        candidates = set()
        for fold in (0, 1):
            local = parsed.replace(tzinfo=zone, fold=fold)
            utc = local.astimezone(timezone.utc)
            if utc.astimezone(zone).replace(tzinfo=None) == parsed:
                candidates.add(utc)
        return next(iter(candidates)) if len(candidates) == 1 else None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


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


def collect_local_context(
    data_dir: Path = DEFAULT_DATA_DIR,
    weather_snapshot: dict[str, Any] | None = None,
    source_snapshots: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Summarize a supplied source set, or read local snapshots for offline callers."""
    if source_snapshots is not None:
        weather_snapshot = source_snapshots.get("meteoswiss_basel_temperature")
        traffic = source_snapshots.get("basel_dataset_100006")
        rhine = source_snapshots.get("basel_dataset_100089")
        port = source_snapshots.get("port_pegel_clean")
    else:
        if weather_snapshot is None:
            weather_snapshot = read_snapshot(data_dir, "meteoswiss_basel_temperature")
        traffic = read_snapshot(data_dir, "basel_dataset_100006")
        rhine = read_snapshot(data_dir, "basel_dataset_100089")
        port = read_snapshot(data_dir, "port_pegel_clean")

    weather = None
    if weather_snapshot:
        station = (weather_snapshot.get("data") or {}).get("station") or {}
        checked_at = weather_snapshot.get("checked_at")
        snapshot_age_minutes = _age_minutes(checked_at)
        observation_age_minutes = _age_minutes(station.get("observed_at_utc") or station.get("observed_at"))
        if observation_age_minutes is None and station.get("age_minutes_at_fetch") is not None:
            try:
                observation_age_minutes = max(0.0, float(station["age_minutes_at_fetch"]) + (snapshot_age_minutes or 0.0))
            except (TypeError, ValueError):
                observation_age_minutes = None
        weather = {
            "observed_at": station.get("observed_at"),
            "age_minutes_at_fetch": station.get("age_minutes_at_fetch"),
            "observation_age_minutes": observation_age_minutes,
            "snapshot_age_minutes": snapshot_age_minutes,
            "station_id": station.get("station_id"),
            "measurements": station.get("measurements") or {},
            "storage": weather_snapshot.get("storage", "local archive"),
            "source_status": ("observed" if observation_age_minutes is not None and observation_age_minutes <= LOCAL_WEATHER_FRESHNESS_MINUTES else "stale")
            if weather_snapshot.get("request_ok") else "unavailable",
        }

    traffic_data = (traffic.get("data") or {}) if traffic else {}
    traffic_results = traffic_data.get("results") or []
    traffic_latest_age = _age_minutes((traffic_results[0].get("datetimeto") or traffic_results[0].get("datetimefrom"))) if traffic_results else None
    traffic_context = {
        "source_status": ("observed snapshot" if traffic_latest_age is not None and traffic_latest_age <= TRAFFIC_FRESHNESS_MINUTES else "stale")
        if traffic and traffic.get("request_ok") else "unknown",
        "latest_record_age_minutes": traffic_latest_age,
        "record_count": len(traffic_results),
        "total_count": traffic_data.get("total_count"),
        "baseline_available": False,
        "interpretation": "Counts alone do not establish congestion or travel time.",
    }

    rhine_results = ((rhine or {}).get("data") or {}).get("results") or []
    latest_rhine = rhine_results[0] if rhine_results else None
    basel_stadt_age = _age_minutes(latest_rhine.get("timestamp")) if latest_rhine else None
    port_data = port or {}
    port_current = next(
        (item for item in port_data.get("current_readings", []) if item.get("name") == "Basel-Rheinhalle"),
        None,
    )
    port_page_checked = (port or {}).get("current_page_checked_at")
    port_snapshot_age = _age_minutes(port_page_checked)
    port_observed = _port_observation_time((port_current or {}).get("observed_at"))
    port_age = None
    port_status = "unknown"
    port_reason = "Port gauge measurement time is missing, invalid, or ambiguous; current freshness is unknown."
    if port_observed is not None:
        elapsed = (datetime.now(timezone.utc) - port_observed).total_seconds() / 60
        if elapsed < 0:
            port_reason = "Port gauge measurement time is in the future; current freshness is unknown."
        else:
            port_age = elapsed
            port_status = "observed snapshot" if port_age <= PORT_GAUGE_FRESHNESS_MINUTES else "stale"
            port_reason = f"Port gauge measurement is {port_age:.1f} min old (demo limit {PORT_GAUGE_FRESHNESS_MINUTES:g} min)."
    thresholds = {item.get("mark"): item for item in port_data.get("flood_thresholds", [])}
    return {
        "weather": weather,
        "traffic": traffic_context,
        "rhine": {
            "basel_stadt_latest": latest_rhine,
            "basel_stadt_observation_age_minutes": basel_stadt_age,
            "port_basel_rheinhalle": port_current,
            "port_snapshot_age_minutes": port_snapshot_age,
            "port_observation_age_minutes": port_age,
            "port_observed_at_utc": port_observed.isoformat() if port_observed is not None else None,
            "port_freshness_reason": port_reason,
            "port_thresholds": thresholds,
            "interpretation": "Separate gauges; apply restrictions only to a matching ship-leg segment.",
            "source_status": port_status,
        },
    }
