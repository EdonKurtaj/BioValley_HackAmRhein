"""Read the risk engine's saved public-data observations from Supabase."""

from __future__ import annotations

import json
import math
import os
import shlex
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ID = "meteoswiss_basel_temperature"
STATION_ID = "BAS"
REQUEST_TIMEOUT_SECONDS = 15
ROW_LIMIT = 100
PAGE_SIZE = 1000


def _load_local_settings(project_root: Path = PROJECT_ROOT) -> None:
    """Load only local .env settings; variables already in the process win."""
    for path in (project_root / ".env", project_root / "pythontest" / ".env"):
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise ValueError(f"Could not read Supabase configuration from {path}: {exc}") from exc
        for line in lines:
            parts = shlex.split(line, comments=True)
            if parts and parts[0] == "export":
                parts = parts[1:]
            if parts and "=" in parts[0]:
                key, value = parts[0].split("=", 1)
                if key in ("SUPABASE_URL", "SUPABASE_SECRET_KEY"):
                    os.environ.setdefault(key, value)


def _observation_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _get_json(url: str, key: str, table: str, query: dict) -> object:
    request = Request(
        f"{url.rstrip('/')}/rest/v1/{table}?{urlencode(query)}",
        headers={"apikey": key, "Accept": "application/json"},
        method="GET",
    )
    if key.count(".") == 2:
        request.add_header("Authorization", f"Bearer {key}")
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        exc.close()
        raise ValueError(f"Supabase {table} read failed: HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise ValueError(f"Supabase {table} read failed: connection unavailable") from None
    except json.JSONDecodeError:
        raise ValueError(f"Supabase {table} read failed: response was not valid JSON") from None


def _credentials(project_root: Path) -> tuple[str, str]:
    _load_local_settings(project_root)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise ValueError("Supabase is the data source; set SUPABASE_URL and SUPABASE_SECRET_KEY in .env")
    if not url.startswith("https://"):
        raise ValueError("SUPABASE_URL must use HTTPS")
    return url, key


def _observations(url: str, key: str, source_id: str, limit: int | None = None) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while limit is None or len(rows) < limit:
        page_limit = PAGE_SIZE if limit is None else min(PAGE_SIZE, limit - len(rows))
        page = _get_json(url, key, "observations", {
            "select": "fetch_run_id,station_id,station_name,observation_key,observed_at,metric,value,unit,dimensions,raw_record",
            "source_id": f"eq.{source_id}",
            "order": "observed_at.desc",
            "limit": str(page_limit),
            "offset": str(offset),
        })
        if not isinstance(page, list):
            raise ValueError(f"Supabase observations for {source_id} must be a list")
        rows.extend(row for row in page if isinstance(row, dict))
        if len(page) < page_limit:
            break
        offset += len(page)
    return rows


def _latest_run(url: str, key: str, source_id: str, *, successful: bool = True) -> dict | None:
    query = {
        "select": "id,source_id,fetched_at,request_ok,http_status,error,raw_payload",
        "source_id": f"eq.{source_id}",
        "order": "fetched_at.desc",
        "limit": "1",
    }
    if successful:
        query["request_ok"] = "eq.true"
    rows = _get_json(url, key, "fetch_runs", query)
    if not isinstance(rows, list):
        raise ValueError(f"Supabase fetch_runs for {source_id} must be a list")
    return rows[0] if rows and isinstance(rows[0], dict) else None


def _weather_snapshot(url: str, key: str) -> dict:
    rows = _get_json(url, key, "observations", {
        "select": "station_id,station_name,observed_at,metric,value,unit,dimensions",
        "source_id": f"eq.{SOURCE_ID}",
        "station_id": f"eq.{STATION_ID}",
        "order": "observed_at.desc",
        "limit": str(ROW_LIMIT),
    })
    if not isinstance(rows, list):
        raise ValueError("Supabase observations response must be a list")
    timed_rows = [(row, _observation_time(row.get("observed_at"))) for row in rows if isinstance(row, dict)]
    timed_rows = [(row, stamp) for row, stamp in timed_rows if stamp is not None]
    if not timed_rows:
        raise ValueError("Supabase has no timestamped MeteoSwiss observations for station BAS")

    latest_time = max(stamp for _, stamp in timed_rows)
    latest_rows = [(row, stamp) for row, stamp in timed_rows if stamp == latest_time]
    measurements = {}
    units = {}
    for row, _ in latest_rows:
        metric = row.get("metric")
        value = row.get("value")
        if not isinstance(metric, str) or isinstance(value, bool):
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(numeric):
            continue
        measurements[metric] = int(numeric) if numeric.is_integer() else numeric
        units[metric] = row.get("unit")
    if not measurements:
        raise ValueError("Supabase's newest MeteoSwiss observation contains no numeric measurements")

    checked_at = datetime.now(timezone.utc).isoformat()
    return {
        "source_id": SOURCE_ID,
        "checked_at": checked_at,
        "request_ok": True,
        "storage": "Supabase observations",
        "data": {"station": {
            "station_id": STATION_ID,
            "station_name": next((row.get("station_name") for row, _ in latest_rows if row.get("station_name")), None),
            "observed_at": latest_time.isoformat(),
            "observed_at_utc": latest_time.isoformat(),
            "measurements": measurements,
            "units": units,
        }},
    }


def _unique_raw_records(rows: list[dict]) -> list[dict]:
    unique = {}
    for row in rows:
        raw = row.get("raw_record")
        if not isinstance(raw, dict):
            continue
        identity = row.get("observation_key") or json.dumps(raw, sort_keys=True, ensure_ascii=False)
        unique[identity] = raw
    return list(unique.values())


def _port_thresholds(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    tables = payload.get("tables") or []
    thresholds = []
    for table in tables:
        if not table:
            continue
        headers = [str(value).casefold() for value in table[0]]
        if "hochwassermarke" not in headers or "abflussmenge basel-rheinhalle" not in headers:
            continue
        for row in table[1:]:
            if len(row) < 3:
                continue
            water = str(row[1]).strip()
            discharge = str(row[2]).strip()
            thresholds.append({"mark": row[0], "water_level": water, "discharge_approx": discharge})
    return thresholds


def fetch_supabase_sources(project_root: Path = PROJECT_ROOT) -> dict:
    """Fetch every source consumed by the assessment; never fall back to local archives."""
    url, key = _credentials(project_root)
    snapshots = {SOURCE_ID: _weather_snapshot(url, key)}

    traffic_id = "basel_dataset_100006"
    traffic_rows = _observations(url, key, traffic_id)
    traffic_results = _unique_raw_records(traffic_rows)
    traffic_results.sort(key=lambda row: _observation_time(row.get("datetimefrom")) or datetime.min.replace(tzinfo=timezone.utc),
                         reverse=True)
    traffic_run = _latest_run(url, key, traffic_id)
    snapshots[traffic_id] = {
        "request_ok": bool(traffic_run and traffic_run.get("request_ok")),
        "checked_at": (traffic_run or {}).get("fetched_at"),
        "data": {"results": traffic_results,
                 "total_count": ((traffic_run or {}).get("raw_payload") or {}).get("total_count")},
        "history_results": traffic_results,
        "storage": "Supabase observations",
    }

    rhine_id = "basel_dataset_100089"
    rhine_rows = _observations(url, key, rhine_id, limit=500)
    rhine_results = _unique_raw_records(rhine_rows)
    rhine_results.sort(key=lambda row: _observation_time(row.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
                       reverse=True)
    rhine_run = _latest_run(url, key, rhine_id)
    snapshots[rhine_id] = {
        "request_ok": bool(rhine_run and rhine_run.get("request_ok")),
        "checked_at": (rhine_run or {}).get("fetched_at"),
        "data": {"results": rhine_results, "total_count": len(rhine_results)},
        "storage": "Supabase observations",
    }

    port_id = "port_pegel_current"
    port_run = _latest_run(url, key, port_id)
    # A successful HTTP fetch can have failed normalization or observation
    # delivery. Read the gauge's stored measurement independently of that run.
    port_rows = _get_json(url, key, "observations", {
        "select": "station_id,station_name,observed_at,metric,value,unit,raw_record,fetch_run_id",
        "source_id": f"eq.{port_id}", "station_id": "eq.Basel-Rheinhalle",
        "metric": "eq.water_level", "value": "not.is.null", "observed_at": "not.is.null",
        "order": "observed_at.desc", "limit": "1",
    })
    if not isinstance(port_rows, list):
        raise ValueError("Supabase port observations response must be a list")
    current_readings = []
    for row in port_rows:
        if not isinstance(row, dict) or row.get("metric") != "water_level":
            continue
        current_readings.append({
            "name": row.get("station_name") or row.get("station_id"),
            "value": row.get("value"), "unit": row.get("unit"),
            "observed_at": row.get("observed_at"),
        })
    snapshots["port_pegel_clean"] = {
        "current_page_checked_at": (port_run or {}).get("fetched_at"),
        "current_readings": current_readings,
        "flood_thresholds": _port_thresholds((port_run or {}).get("raw_payload")),
        "storage": "Supabase observations",
    }

    road_id = "opentransportdata_basel_region"
    road_run = _latest_run(url, key, road_id)
    road_payload = (road_run or {}).get("raw_payload")
    snapshots[road_id] = {
        "request_ok": bool(road_run and road_run.get("request_ok")),
        "checked_at": (road_run or {}).get("fetched_at"),
        "data": road_payload if isinstance(road_payload, dict) else {},
        "storage": "Supabase fetch_runs",
    }
    return snapshots


def fetch_latest_weather_snapshot(project_root: Path = PROJECT_ROOT) -> dict:
    """Backward-compatible helper for callers that need only the weather batch."""
    url, key = _credentials(project_root)
    return _weather_snapshot(url, key)
