"""Read the newest MeteoSwiss observation from the existing Supabase archive."""

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


def fetch_latest_weather_snapshot(project_root: Path = PROJECT_ROOT) -> dict:
    """Fetch one latest-time MeteoSwiss station batch without exposing credentials."""
    _load_local_settings(project_root)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise ValueError("Supabase weather is the default; set SUPABASE_URL and SUPABASE_SECRET_KEY in .env")
    if not url.startswith("https://"):
        raise ValueError("SUPABASE_URL must use HTTPS")

    query = urlencode({
        "select": "station_id,station_name,observed_at,metric,value,unit,dimensions",
        "source_id": f"eq.{SOURCE_ID}",
        "station_id": f"eq.{STATION_ID}",
        "order": "observed_at.desc",
        "limit": str(ROW_LIMIT),
    })
    request = Request(
        f"{url.rstrip('/')}/rest/v1/observations?{query}",
        headers={"apikey": key, "Accept": "application/json"},
        method="GET",
    )
    if key.count(".") == 2:
        request.add_header("Authorization", f"Bearer {key}")
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            rows = json.loads(response.read())
    except HTTPError as exc:
        raise ValueError(f"Supabase weather read failed: HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("Supabase weather read failed: connection unavailable") from None
    except json.JSONDecodeError:
        raise ValueError("Supabase weather read failed: response was not valid JSON") from None

    if not isinstance(rows, list):
        raise ValueError("Supabase weather read failed: observations response must be a list")
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
