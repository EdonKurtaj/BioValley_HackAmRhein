"""Present observed regional signals or explicitly simulated shipment evidence."""

from datetime import datetime, timezone
from math import isfinite

from .config import (
    COLD_AMBIENT_ONSET_C, HOT_AMBIENT_ONSET_C, LOCAL_WEATHER_FRESHNESS_MINUTES,
    PORT_GAUGE_FRESHNESS_MINUTES, RHINE_PRE_ALERT_CM, ROAD_EVENT_FRESHNESS_MINUTES,
    STRONG_GUST_ONSET_KMH,
)
from .demo import demo_fleet
from .local_data import collect_local_context
from .supabase_data import fetch_supabase_sources

MAP_LOCATIONS = [
    {"id": "port", "name": "Basel-Rheinhalle", "category": "port", "latitude": 47.587,
     "longitude": 7.596, "description": "Port-Pegel; Position dient der Orientierung."},
    {"id": "rhine", "name": "Rhein · Mittlere Brücke", "category": "river", "latitude": 47.5618,
     "longitude": 7.5895, "description": "Rheinkorridor; Pegel ist kein Beleg für eine LKW-Routenstörung."},
    {"id": "weather", "name": "Basel / Binningen", "category": "weather", "latitude": 47.5411,
     "longitude": 7.5836, "description": "Regionaler Wetterkontext; keine Pakettemperatur."},
]


def _time(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp if stamp.tzinfo is not None and stamp.utcoffset() is not None else None
    except (ValueError, AttributeError, TypeError):
        return None


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if isfinite(number) else None
    except (ValueError, TypeError):
        return None


def _freshness(at, now, limit):
    stamp = _time(at)
    if stamp is None or stamp > now:
        return "unknown"
    return "current" if (now - stamp).total_seconds() <= limit * 60 else "stale"


def _signal(identity, title, value, unit, at, freshness, source, detail, elevated=False):
    return {"id": identity, "title": title, "value": value, "unit": unit, "observedAt": at,
            "freshness": freshness, "source": source, "detail": detail,
            "severity": "unknown" if value is None or freshness != "current" else "warning" if elevated else "normal"}


def live_dashboard(sources=None, *, now=None) -> dict:
    """Read Supabase only. Regional events are not automatically shipment matches."""
    now = now or datetime.now(timezone.utc)
    sources = fetch_supabase_sources() if sources is None else sources
    context = collect_local_context(source_snapshots=sources)
    weather = context.get("weather") or {}
    weather_at = weather.get("observed_at")
    weather_freshness = _freshness(weather_at, now, LOCAL_WEATHER_FRESHNESS_MINUTES)
    if weather.get("source_status") == "unavailable" or (
            weather.get("source_status") != "observed" and weather_freshness == "current"):
        weather_freshness = "unknown"
    values = weather.get("measurements") or {}
    temperature = _number(values.get("tre200s0"))
    gust = _number(values.get("fu3010z1"))
    rhine = context.get("rhine") or {}
    port = rhine.get("port_basel_rheinhalle") or {}
    port_at = rhine.get("port_observed_at_utc")
    port_freshness = _freshness(port_at, now, PORT_GAUGE_FRESHNESS_MINUTES)
    level = _number(port.get("value"))
    road_snapshot = sources.get("opentransportdata_basel_region") or {}
    road = road_snapshot.get("data") or {}
    road_at = road.get("fetched_at")
    road_freshness = _freshness(road_at, now, ROAD_EVENT_FRESHNESS_MINUTES)
    errors = road.get("errors") or []
    if (not road_snapshot.get("request_ok") and not errors) or any(str(error).startswith("Traffic Situations:") for error in errors):
        road_freshness = "unknown"
    events = road.get("traffic_situations") or []
    alerts = []
    event_locations = []
    for event in events:
        descriptions = [str(item) for item in event.get("descriptions", [])]
        # Do not present revoked or expired source messages as active incidents.
        if any(item.casefold().startswith(("aufgehoben:", "revoked:", "révoqué:", "revocato:")) for item in descriptions):
            continue
        end = _time(event.get("valid_until"))
        start = _time(event.get("valid_from"))
        if (end and end <= now) or (start and start > now):
            continue
        active = event.get("validity_status") in ("active", "definedByValidityTimeSpec")
        updated = _time(event.get("updated_at"))
        valid_end = event.get("valid_until") is None or end is not None
        event_freshness = (road_freshness if active and start and updated and updated <= now
                           and valid_end and not event.get("complex_validity") else "unknown")
        title = descriptions[0] if descriptions else str(event.get("type") or "Verkehrsmeldung")
        identity = str(event.get("id") or f"event-{len(alerts)}")
        alerts.append({"id": identity, "title": title, "detail": "Regionale Meldung · Routenbezug, Richtung und Fahrzeugklasse prüfen.",
                       "kind": "traffic", "observedAt": event.get("updated_at"), "freshness": event_freshness})
        # Only confirmed active observations become incident markers.
        for point in (event.get("local_coordinates", [])[:1] if event_freshness == "current" else []):
            latitude, longitude = _number(point.get("latitude")), _number(point.get("longitude"))
            if latitude is not None and longitude is not None and abs(latitude) <= 90 and abs(longitude) <= 180:
                event_locations.append({"id": f"traffic-{identity}", "name": title, "category": "traffic",
                                        "latitude": latitude, "longitude": longitude,
                                        "description": "Regionale Verkehrsmeldung; Routenbezug prüfen."})
    alerts.sort(key=lambda alert: {"current": 0, "stale": 1, "unknown": 2}[alert["freshness"]])
    current_event_count = sum(alert["freshness"] == "current" for alert in alerts)
    signals = [
        _signal("temperature", "Lufttemperatur", temperature, "°C", weather_at, weather_freshness,
                "MeteoSwiss · Supabase", "Basel/Binningen · Umgebung, kein Paketsensor", temperature is not None and (temperature >= HOT_AMBIENT_ONSET_C or temperature <= COLD_AMBIENT_ONSET_C)),
        _signal("traffic", "Verkehrsmeldungen", current_event_count if road_freshness == "current" else None, "aktuell", road_at,
                road_freshness, "OpenTransportData · Supabase", "Regionale Kandidaten, kein automatischer Routenbezug", current_event_count > 0),
        _signal("gust", "Windböen", gust, "km/h", weather_at, weather_freshness,
                "MeteoSwiss · Supabase", "Kontext für exponierten Umschlag", gust is not None and gust >= STRONG_GUST_ONSET_KMH),
        _signal("rhine", "Rheinpegel", level, "cm", port_at, port_freshness,
                "Port of Switzerland · Supabase", "Basel-Rheinhalle · betrifft passende Schiffsabschnitte", level is not None and level >= RHINE_PRE_ALERT_CM),
    ]
    return {"mode": "live", "updatedAt": now.isoformat(), "locations": [*MAP_LOCATIONS, *event_locations],
            "signals": signals, "alerts": alerts[:30], "shipments": [], "simulation": None,
            "sourceLabel": "Gespeicherte Supabase-Beobachtungen", "transportSource": "Kein GPS-/Paketsensor-Feed verbunden"}


def demo_dashboard(anchor: datetime, elapsed_minutes=0, scenario="fleet") -> dict:
    fleet = demo_fleet(anchor, elapsed_minutes, scenario)
    stamp = fleet["updatedAt"]
    air = 40 if scenario == "heat" else 18.4 if scenario == "normal" else 35
    delays = [shipment for shipment in fleet["shipments"] if shipment["delayMinutes"] > 0 and shipment["status"] != "delivered"]
    alerts = [{"id": f"jam-{shipment['id']}", "title": f"Stau · {shipment['routeName']}",
               "detail": f"Simulierte Verzögerung {shipment['delayMinutes']:g} min · {shipment['id']}",
               "kind": "traffic", "observedAt": stamp, "freshness": "current"} for shipment in delays]
    if air >= HOT_AMBIENT_ONSET_C:
        alerts.append({"id": "heat", "title": "Hohe Außentemperatur", "detail": "Simuliert · Kühlung und Umschlagfenster prüfen; Paketmessung bleibt separat.",
                       "kind": "weather", "observedAt": stamp, "freshness": "current"})
    locations = [*MAP_LOCATIONS, *[{"id": alert["id"], "name": alert["title"], "category": "traffic",
                                  "longitude": shipment["route"][3][0], "latitude": shipment["route"][3][1],
                                  "description": alert["detail"]} for shipment, alert in zip(delays, alerts)]]
    return {"mode": "demo", **fleet, "locations": locations, "alerts": alerts,
            "signals": [
                _signal("temperature", "Lufttemperatur", air, "°C", stamp, "current", "Demo-Wetter", "Synthetisches Umgebungssignal", air >= HOT_AMBIENT_ONSET_C),
                _signal("traffic", "Routenstörungen", len(delays), "Stau", stamp, "current", "Demo-Verkehr", "Explizit den Demo-LKW zugeordnet", bool(delays)),
                _signal("gust", "Windböen", 12, "km/h", stamp, "current", "Demo-Wetter", "Synthetische Messung"),
                _signal("rhine", "Rheinpegel", 479, "cm", stamp, "current", "Demo-Pegel", "Kontext · kein Einfluss auf Demo-LKW"),
            ], "sourceLabel": "Synthetische Messungen, GPS, Routen und Paketdaten", "transportSource": "Simulierte LKW-Flotte"}
