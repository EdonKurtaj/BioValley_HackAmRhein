"""Pure normalization of public source payloads into observation rows."""

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from interfaces import FetchResult, Observation
from transform_port_pegel import parse_current, parse_forecast

RHINE_UNITS = {"abfluss": "m3/s", "pegelhoehe": "cm", "pegel": "m"}
TRAFFIC_METRICS = (
    "total", "mr", "pw", "pw0", "lief", "lief0", "lief_aufl",
    "lw", "lw0", "sattelzug", "bus", "andere",
)
ZURICH = ZoneInfo("Europe/Zurich")
WINTER_TIME = timezone(timedelta(hours=1))


def utc_time(value: str, local_zone=ZURICH) -> str:
    """Keep explicit offsets; apply the source timezone only to local timestamps."""
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        timestamp = None
        for pattern in ("%d.%m.%Y %H:%M", "%d.%m.%Y - %H:%M"):
            try:
                timestamp = datetime.strptime(value, pattern)
                break
            except ValueError:
                continue
        if timestamp is None:
            raise ValueError(f"Unsupported observation timestamp: {value!r}")
    if timestamp.tzinfo is None:
        if timestamp.replace(tzinfo=local_zone, fold=0).utcoffset() != timestamp.replace(tzinfo=local_zone, fold=1).utcoffset():
            raise ValueError(f"Ambiguous or nonexistent local timestamp: {value!r}")
        timestamp = timestamp.replace(tzinfo=local_zone)
    return timestamp.astimezone(timezone.utc).isoformat()


def observation(result: FetchResult, station: str, name: str | None, timestamp: str,
                metric: str, value: object, unit: str, raw: dict,
                dimensions: dict | None = None, identity: object = None) -> Observation | None:
    """Build a stable identity without conflating traffic lanes or forecast issues."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Non-numeric value for {metric}")
    identity_text = json.dumps([station, timestamp, identity], sort_keys=True, ensure_ascii=False)
    return {
        "source_id": result["source_id"],
        "observation_key": hashlib.sha256(identity_text.encode()).hexdigest(),
        "observed_at": timestamp, "station_id": station, "station_name": name,
        "metric": metric, "value": value, "unit": unit,
        "dimensions": dimensions or {}, "raw_record": raw,
    }


def normalize_meteo(result: FetchResult) -> list[Observation]:
    data = result["data"]
    station = data["station"]
    timestamp = utc_time(station["observed_at_utc"])
    rows = []
    for metric, value in station["measurements"].items():
        metadata = data["parameter_metadata"][metric]
        dimensions = {key: metadata[key] for key in ("aggregation", "interval_minutes") if key in metadata}
        row = observation(result, station["station_id"], station.get("station_name"), timestamp,
                          metric, value, metadata["unit"], station, dimensions)
        if row:
            rows.append(row)
    return rows


def normalize_rhine(result: FetchResult) -> list[Observation]:
    rows = []
    for raw in result["data"]["results"]:
        timestamp = utc_time(raw["timestamp"])
        for metric, unit in RHINE_UNITS.items():
            row = observation(result, "basel-rheinhalle", "Basel-Rheinhalle", timestamp,
                              metric, raw.get(metric), unit, raw)
            if row:
                rows.append(row)
    return rows


def normalize_traffic(result: FetchResult) -> list[Observation]:
    rows = []
    for raw in result["data"]["results"]:
        station = str(raw.get("sitecode") or raw.get("zst_id") or raw["zst_nr"])
        timestamp = utc_time(raw["datetimefrom"])
        dimensions = {key: raw.get(key) for key in (
            "lanecode", "lanename", "directionname", "traffictype", "datetimeto",
            "valuesapproved", "valuesedited",
        )}
        identity = {key: raw.get(key) for key in ("lanecode", "directionname", "traffictype", "datetimeto")}
        for metric in TRAFFIC_METRICS:
            row = observation(result, station, raw.get("sitename"), timestamp,
                              metric, raw.get(metric), "vehicles", raw, dimensions, identity)
            if row:
                rows.append(row)
    return rows


def normalize_opentransportdata(result: FetchResult) -> list[Observation]:
    """Normalize numeric Basel-region OTD counter readings; events stay in raw payload."""
    data = result["data"]
    counters = data["traffic_counters"]
    sites = {site.get("id"): site for site in counters["sites"] if site.get("id")}
    rows = []
    for reading in counters["current_readings"]:
        timestamp = reading.get("observed_at")
        if not timestamp:
            continue
        observed_at = utc_time(timestamp)
        site_id = reading["site_id"]
        site = sites.get(site_id, {})
        for measured in reading["values"]:
            meaning = measured.get("meaning")
            if meaning.endswith("_flow_per_hour"):
                metric, field_name, unit = meaning, "vehicleFlowRate", "vehicles/hour"
            elif meaning.endswith("_average_speed_kmh"):
                metric, field_name, unit = meaning, "speed", "km/h"
            else:
                continue
            raw_value = measured.get("fields", {}).get(field_name)
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            if value.is_integer():
                value = int(value)
            dimensions = {
                "measurement_index": measured.get("index"),
                "coordinates": site.get("coordinates", []),
                "lanes": site.get("lanes"),
                "sample_count": measured.get("fields", {}).get("numberOfInputValuesUsed"),
            }
            row = observation(result, site_id, None, observed_at, metric, value, unit,
                              {"reading": reading, "measurement": measured}, dimensions,
                              measured.get("index"))
            if row:
                rows.append(row)
    return rows


def normalize_port_current(result: FetchResult) -> list[Observation]:
    readings, _ = parse_current(result["data"]["tables"])
    rows = []
    for reading in readings:
        station = reading["name"]
        row = observation(result, station, station, utc_time(reading["observed_at"]),
                          "water_level", reading["value"], reading["unit"], reading)
        if row:
            rows.append(row)
    return rows


def normalize_port_forecast(result: FetchResult) -> list[Observation]:
    forecast = parse_forecast(result["data"]["tables"], result["data"]["text"])
    zone_text = forecast["time_zone"] or ""
    if "MEWZ" in zone_text or "HHEC" in zone_text:
        local_zone = WINTER_TIME
    elif "UTC" in zone_text:
        local_zone = timezone.utc
    elif "MESZ" in zone_text or "HAEC" in zone_text:
        local_zone = timezone(timedelta(hours=2))
    else:
        raise ValueError("Forecast timezone is missing or unsupported")
    issued = forecast["issued_at"]
    match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4}),?\s*(\d{1,2})[.:](\d{2})", issued or "")
    if not match:
        raise ValueError("Forecast issue timestamp is missing or unsupported")
    issued_at = utc_time(f"{match[1]} {match[2]}:{match[3]}", local_zone)
    dimensions = {"is_forecast": True, "issued_at": issued_at, "source_time_zone": zone_text}
    rows = []
    for raw in forecast["rows"]:
        timestamp = utc_time(raw["time"], local_zone)
        for metric, unit in (("water_level_m_above_sea_level", "m"), ("discharge_m3_per_second", "m3/s")):
            row = observation(result, "basel-rheinhalle", "Basel-Rheinhalle", timestamp,
                              metric, raw[metric], unit, raw, dimensions, issued_at)
            if row:
                rows.append(row)
    return rows


NORMALIZERS = {
    "meteoswiss_basel_temperature": normalize_meteo,
    "basel_dataset_100089": normalize_rhine,
    "basel_dataset_100006": normalize_traffic,
    "opentransportdata_basel_region": normalize_opentransportdata,
    "port_pegel_current": normalize_port_current,
    "port_pegel_forecast": normalize_port_forecast,
}


def normalize(result: FetchResult) -> list[Observation]:
    """Failed fetches create no observations; do not ingest stale local snapshots."""
    if not result["request_ok"]:
        return []
    rows = NORMALIZERS[result["source_id"]](result)
    unique = {(row["observation_key"], row["metric"]): row for row in rows}
    return list(unique.values())
