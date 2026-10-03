#!/usr/bin/env python3
"""Fetch OpenTransportData road signals and retain Basel-Stadt candidates."""

from __future__ import annotations

import gzip
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.sax.saxutils import quoteattr
from xml.etree import ElementTree as ET

from supabase_ingest import load_local_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "pythontest" / "data" / "opentransportdata"
SITE_CACHE = OUTPUT_DIR / "basel_region_sites.json"
COUNTER_HISTORY = OUTPUT_DIR / "counter_history.jsonl"
PULL_URL = "https://api.opentransportdata.swiss/TDP/Soap_Datex2/Pull"
SITUATIONS_URL = "https://api.opentransportdata.swiss/TDP/Soap_Datex2/TrafficSituations/Pull"
DATE_NAMESPACE = "http://datex2.eu/schema/2/2_0"
SOAP_NAMESPACE = "http://schemas.xmlsoap.org/soap/envelope/"
BASEL_TERMS = (
    "basel", "riehen", "bettingen", "weil am rhein", "lörrach", "loerrach",
    "eimeldingen", "saint-louis", "st-louis", "mulhouse", "blotzheim",
    "birsfelden", "muttenz", "pratteln", "augst", "liestal", "sissach",
    "rheinfelden", "möhlin", "moehlin", "frick", "laufenburg", "delémont",
    "delemont", "porrentruy", "eiken", "stein-säckingen", "bad säckingen",
    "egerkingen", "härkingen", "haerkingen", "olten", "verzweigung gellert",
    "verzweigung wiese", "basel-breite", "basel-wettstein", "basel-rheinhafen",
    "basel-badischer bahnhof", "basel-kleinhuningen", "basel-kleinhüningen",
    "basel-st. johann", "basel-st johann", "basel-euroairport",
)
BASEL_CENTER = (47.5596, 7.5886)
BASEL_REGION_RADIUS_KM = 55.0
SITE_CACHE_MAX_AGE_HOURS = 168.0
SUMMARY_LIMIT = 8
COUNTER_VALUE_LABELS = {
    "1": "unclassified_vehicle_flow_per_hour",
    "2": "invalid_speed_measurement",
    "11": "light_vehicle_flow_per_hour",
    "12": "light_vehicle_average_speed_kmh",
    "21": "heavy_goods_flow_per_hour",
    "22": "heavy_goods_average_speed_kmh",
}
TIMEOUT_SECONDS = 45


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if local_name(child.tag) == name and child.text and child.text.strip():
            return child.text.strip()
    return None


def distance_from_basel_km(latitude: float, longitude: float) -> float:
    """Return great-circle distance from Basel city centre to a coordinate."""
    lat1, lon1 = map(radians, BASEL_CENTER)
    lat2, lon2 = radians(latitude), radians(longitude)
    delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
    haversine = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(haversine))


def is_in_basel_region(latitude: float, longitude: float) -> bool:
    """Include counter sites within the Basel metro area and inbound corridors."""
    return distance_from_basel_km(latitude, longitude) <= BASEL_REGION_RADIUS_KM


def coordinates(element: ET.Element) -> list[dict[str, float]]:
    points = []
    for point in element.iter():
        if local_name(point.tag) != "pointCoordinates":
            continue
        latitude = child_text(point, "latitude")
        longitude = child_text(point, "longitude")
        try:
            if latitude is not None and longitude is not None:
                points.append({"latitude": float(latitude), "longitude": float(longitude)})
        except ValueError:
            continue
    return points


def extract_counter_sites(xml_payload: bytes) -> list[dict]:
    """Read the counter master table and keep records whose coordinates are local."""
    root = ET.fromstring(xml_payload)
    sites = []
    for record in root.iter():
        if local_name(record.tag) != "measurementSiteRecord":
            continue
        points = coordinates(record)
        local_points = [point for point in points if is_in_basel_region(point["latitude"], point["longitude"])]
        if not local_points:
            continue
        sites.append({
            "id": record.attrib.get("id"),
            "version": record.attrib.get("version"),
            "coordinates": local_points,
            "lanes": child_text(record, "measurementSiteNumberOfLanes"),
            "characteristics": [
                {"index": item.attrib.get("index"),
                 "type": child_text(item, "specificMeasurementValueType"),
                 "vehicle": child_text(item, "vehicleType")}
                for item in record.iter() if local_name(item.tag) == "measurementSpecificCharacteristics"
                and item.attrib.get("index")
            ],
        })
    return sites


def extract_counter_readings(xml_payload: bytes, local_site_ids: set[str]) -> list[dict]:
    """Extract current count/speed values only for Basel-Stadt master-table sites."""
    root = ET.fromstring(xml_payload)
    readings = []
    for site in root.iter():
        if local_name(site.tag) != "siteMeasurements":
            continue
        reference = next((item for item in site.iter() if local_name(item.tag) == "measurementSiteReference"), None)
        site_id = reference.attrib.get("id") if reference is not None else None
        if site_id not in local_site_ids:
            continue
        values = []
        for measured in site.iter():
            if local_name(measured.tag) != "measuredValue" or "index" not in measured.attrib:
                continue
            values.append({
                "index": measured.attrib["index"],
                "meaning": COUNTER_VALUE_LABELS.get(measured.attrib["index"], "other_counter_measurement"),
                "fields": {local_name(item.tag): item.text.strip()
                           for item in measured.iter() if item is not measured
                           and item.text and item.text.strip()
                           and local_name(item.tag) in {"vehicleFlowRate", "speed", "numberOfInputValuesUsed"}},
            })
        readings.append({"site_id": site_id, "observed_at": child_text(site, "measurementTimeDefault"),
                         "values": values})
    return readings


def extract_basel_situations(xml_payload: bytes) -> list[dict]:
    """Keep traffic situation records mentioning Basel localities or carrying local coordinates."""
    root = ET.fromstring(xml_payload)
    situations = []
    for record in root.iter():
        if local_name(record.tag) != "situationRecord":
            continue
        searchable = " ".join(part.strip() for part in record.itertext() if part and part.strip())
        normalized = re.sub(r"\s+", " ", searchable).casefold()
        local_points = [point for point in coordinates(record)
                       if is_in_basel_region(point["latitude"], point["longitude"])]
        term_matches = [term for term in BASEL_TERMS if term in normalized]
        if not local_points and not term_matches:
            continue
        description = []
        for comment in record.iter():
            if local_name(comment.tag) != "generalPublicComment":
                continue
            for node in comment.iter():
                if local_name(node.tag) == "value" and node.text and node.text.strip():
                    description.append(node.text.strip())
        unique_descriptions = list(dict.fromkeys(description))
        situations.append({
            "id": record.attrib.get("id"),
            "type": record.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type"),
            "created_at": child_text(record, "situationRecordCreationTime"),
            "updated_at": child_text(record, "situationRecordVersionTime"),
            "validity_status": child_text(record, "validityStatus"),
            "complex_validity": any(local_name(item.tag) in {
                "validPeriod", "exceptionPeriod", "recurringTimePeriodOfDay", "recurringDayWeekMonthPeriod"
            } for item in record.iter()),
            "valid_from": child_text(record, "overallStartTime"),
            "valid_until": child_text(record, "overallEndTime"),
            "descriptions": unique_descriptions,
            "local_coordinates": local_points,
            "basel_term_matches": term_matches,
            "filter_match": "coordinate within Basel 55 km region" if local_points else "Basel-region place name in event text; verify location",
        })
    return situations


def _soap_envelope(body: str) -> bytes:
    return (f'<soap:Envelope xmlns:soap="{SOAP_NAMESPACE}" xmlns:dx="{DATE_NAMESPACE}" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f"<soap:Body>{body}</soap:Body></soap:Envelope>").encode("utf-8")


def measurement_table_request() -> bytes:
    return _soap_envelope(
        '<dx:d2LogicalModel modelBaseVersion="2"><dx:exchange><dx:supplierIdentification>'
        '<dx:country>ch</dx:country><dx:nationalIdentifier>OTD</dx:nationalIdentifier>'
        '</dx:supplierIdentification></dx:exchange></dx:d2LogicalModel>'
    )


def measured_data_request(site_ids: list[str]) -> bytes:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    references = "".join(
        f'<dx:siteRequestReference targetClass="MeasurementSiteRecord" id={quoteattr(site_id)} version="0"/>'
        for site_id in site_ids
    )
    payload = (
        '<dx:d2LogicalModel modelBaseVersion="2"><dx:exchange><dx:supplierIdentification>'
        '<dx:country>ch</dx:country><dx:nationalIdentifier>OTD</dx:nationalIdentifier>'
        '</dx:supplierIdentification></dx:exchange>'
        '<dx:payloadPublication xsi:type="dx:GenericPublication" lang="en">'
        f'<dx:publicationTime>{now}</dx:publicationTime><dx:publicationCreator>'
        '<dx:country>ch</dx:country><dx:nationalIdentifier>OTD</dx:nationalIdentifier>'
        '</dx:publicationCreator><dx:genericPublicationName>MeasuredDataFilter</dx:genericPublicationName>'
        '<dx:genericPublicationExtension><dx:measuredDataFilter>'
        '<dx:measurementSiteTableReference targetClass="MeasurementSiteTable" id="OTD:TrafficData" version="0"/>'
        f"{references}</dx:measuredDataFilter></dx:genericPublicationExtension></dx:payloadPublication></dx:d2LogicalModel>"
    )
    return _soap_envelope(payload)


def _read_cached_sites(refresh: bool) -> list[dict] | None:
    if refresh or not SITE_CACHE.exists():
        return None
    try:
        cached = json.loads(SITE_CACHE.read_text(encoding="utf-8"))
        age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(cached["cached_at"])).total_seconds() / 3600
        if age_hours <= SITE_CACHE_MAX_AGE_HOURS:
            return cached.get("sites") or []
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return None
    return None


def _save_sites(sites: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SITE_CACHE.write_text(json.dumps({"cached_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                      "region_radius_km": BASEL_REGION_RADIUS_KM, "sites": sites},
                                     ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _request(url: str, api_key: str, soap_action: str, body: bytes | None = None) -> bytes:
    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "BioValley-HackAmRhein/1.0",
               "Content-Type": "application/xml", "SOAPAction": soap_action}
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = response.read()
            content_encoding = response.headers.get("Content-Encoding", "").lower()
            if "gzip" in content_encoding or payload.startswith(b"\x1f\x8b"):
                try:
                    payload = gzip.decompress(payload)
                except OSError:
                    raise RuntimeError("OpenTransportData returned a damaged gzip response") from None
            try:
                ET.fromstring(payload)
            except ET.ParseError:
                preview = payload[:240].decode("utf-8", errors="replace")
                preview = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", preview)
                preview = re.sub(r"\s+", " ", preview).strip().replace(api_key, "[redacted]")
                preview = preview.replace(f"Bearer {api_key}", "Bearer [redacted]")[:160]
                content_type = response.headers.get("Content-Type", "unknown")
                raise RuntimeError(
                    f"OpenTransportData returned HTTP {response.status} with non-XML content "
                    f"({content_type}): {preview or 'empty response'}"
                ) from None
            return payload
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        detail = re.sub(r"<[^>]+>", " ", detail)
        detail = re.sub(r"\s+", " ", detail).strip()
        detail = detail.replace(api_key, "[redacted]")[:240]
        exc.close()
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"OpenTransportData returned HTTP {exc.code} for {url.rsplit('/', 1)[-1]}{suffix}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"OpenTransportData request failed ({type(exc).__name__})") from None


def fetch_all(refresh_sites: bool = False) -> dict:
    load_local_env()
    situation_key = os.environ.get("OTD_TRAFFIC_SITUATIONS_API_KEY")
    counters_key = os.environ.get("OTD_TRAFFIC_COUNTERS_API_KEY")
    missing = [name for name, value in (("OTD_TRAFFIC_SITUATIONS_API_KEY", situation_key),
                                         ("OTD_TRAFFIC_COUNTERS_API_KEY", counters_key)) if not value]
    if missing:
        raise RuntimeError("Missing .env setting(s): " + ", ".join(missing))

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "filter": {"area": "Basel region including inbound/outbound route alternatives",
                   "method": "counter/event coordinates within 55 km of Basel, plus traffic-event text matching Basel-region towns and road junctions",
                   "center": {"latitude": BASEL_CENTER[0], "longitude": BASEL_CENTER[1]},
                   "radius_km": BASEL_REGION_RADIUS_KM},
        "traffic_situations": [], "traffic_counters": {"sites": [], "current_readings": []}, "errors": [],
    }
    situation_started = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    situation_body = (
        '<dx:d2LogicalModel modelBaseVersion="2"><dx:exchange><dx:supplierIdentification>'
        '<dx:country>ch</dx:country><dx:nationalIdentifier>FEDRO</dx:nationalIdentifier>'
        '</dx:supplierIdentification><dx:subscription><dx:operatingMode>operatingMode1</dx:operatingMode>'
        f"<dx:subscriptionStartTime>{situation_started}</dx:subscriptionStartTime>"
        '<dx:subscriptionState>active</dx:subscriptionState><dx:updateMethod>singleElementUpdate</dx:updateMethod>'
        '<dx:target><dx:protocol>http</dx:protocol></dx:target></dx:subscription></dx:exchange></dx:d2LogicalModel>'
    )
    try:
        situation_xml = _request(SITUATIONS_URL, situation_key,
                                 "http://opentransportdata.swiss/TDP/Soap_Datex2/Pull/v1/pullTrafficMessages",
                                 _soap_envelope(situation_body))
        result["traffic_situations"] = extract_basel_situations(situation_xml)
    except (ET.ParseError, RuntimeError) as exc:
        result["errors"].append(f"Traffic Situations: {exc}")

    try:
        sites = _read_cached_sites(refresh_sites)
        if sites is None:
            table_xml = _request(PULL_URL, counters_key,
                                 "http://opentransportdata.swiss/TDP/Soap_Datex2/Pull/v1/pullMeasurementSiteTable",
                                 measurement_table_request())
            sites = extract_counter_sites(table_xml)
            _save_sites(sites)
        result["traffic_counters"]["sites"] = sites
        site_ids = sorted({site["id"] for site in sites if site.get("id")})
        if site_ids:
            readings_xml = _request(PULL_URL, counters_key,
                                    "http://opentransportdata.swiss/TDP/Soap_Datex2/Pull/v1/pullMeasuredData",
                                    measured_data_request(site_ids))
            result["traffic_counters"]["current_readings"] = extract_counter_readings(readings_xml, set(site_ids))
    except (ET.ParseError, RuntimeError) as exc:
        result["errors"].append(f"Traffic Counters: {exc}")
    return result


def _append_counter_history(result: dict) -> int:
    """Archive each new per-minute counter record once for future baselines."""
    previous_keys = set()
    latest_path = OUTPUT_DIR / "latest.json"
    if latest_path.exists():
        try:
            previous = json.loads(latest_path.read_text(encoding="utf-8"))
            previous_keys = {(row.get("site_id"), row.get("observed_at"))
                             for row in previous.get("traffic_counters", {}).get("current_readings", [])}
        except (OSError, json.JSONDecodeError):
            previous_keys = set()
    new_rows = [row for row in result["traffic_counters"]["current_readings"]
                if (row.get("site_id"), row.get("observed_at")) not in previous_keys]
    if new_rows:
        with COUNTER_HISTORY.open("a", encoding="utf-8") as history:
            for row in new_rows:
                history.write(json.dumps({"fetched_at": result["fetched_at"], **row}, ensure_ascii=False) + "\n")
    return len(new_rows)


def save_snapshot(result: dict) -> int:
    """Save a parsed snapshot and append newly observed counter minutes."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    history_rows = _append_counter_history(result)
    output = OUTPUT_DIR / "latest.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return history_rows


def run_once(refresh_sites: bool = False) -> tuple[int, dict]:
    result = fetch_all(refresh_sites)
    history_rows = save_snapshot(result)
    output = OUTPUT_DIR / "latest.json"
    print(f"Saved {len(result['traffic_situations'])} Basel-region traffic situations, "
          f"{len(result['traffic_counters']['sites'])} counter sites, and "
          f"{len(result['traffic_counters']['current_readings'])} current readings "
          f"({history_rows} new history rows) to {output.relative_to(PROJECT_ROOT)}")
    for error in result["errors"]:
        print(f"- {error}", file=sys.stderr)
    for situation in result["traffic_situations"][:SUMMARY_LIMIT]:
        descriptions = "; ".join(situation["descriptions"][:2]) or situation["type"] or "Traffic event"
        print(f"- Situation ({situation['filter_match']}): {descriptions[:220]}")
    for reading in result["traffic_counters"]["current_readings"][:SUMMARY_LIMIT]:
        print(f"- Counter {reading['site_id']} at {reading['observed_at']}: {len(reading['values'])} measured values")
    if len(result["traffic_situations"]) > SUMMARY_LIMIT or len(result["traffic_counters"]["current_readings"]) > SUMMARY_LIMIT:
        print(f"- Full parsed results are in {output.relative_to(PROJECT_ROOT)}")
    return (1 if result["errors"] else 0), result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="repeat collection every minute and archive new counter readings")
    parser.add_argument("--interval-seconds", type=int, default=60, help="watch interval; minimum 60 seconds")
    parser.add_argument("--refresh-sites", action="store_true", help="refresh the cached counter locations now")
    args = parser.parse_args()
    if args.interval_seconds < 60:
        parser.error("--interval-seconds must be at least 60 to respect the feed update cadence")
    try:
        exit_code, _ = run_once(args.refresh_sites)
        if not args.watch:
            return exit_code
        while True:
            cycle_started = time.monotonic()
            try:
                run_once()
            except (ET.ParseError, OSError, RuntimeError) as exc:
                print(f"OpenTransportData fetch failed: {exc}", file=sys.stderr)
            time.sleep(max(0.0, args.interval_seconds - (time.monotonic() - cycle_started)))
    except (ET.ParseError, OSError, RuntimeError) as exc:
        print(f"OpenTransportData fetch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
