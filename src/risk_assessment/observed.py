"""Score current open-data signals without simulating package or route data."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from math import isfinite
from pathlib import Path

from .config import (
    OPEN_RHINE_WEIGHT,
    OPEN_TRAFFIC_WEIGHT,
    OPEN_URGENCY_WEIGHT,
    OPEN_WEATHER_WEIGHT,
    RHINE_PRE_ALERT_CM,
    RHINE_RESTRICTION_CM,
    TRAFFIC_ANOMALY_THRESHOLD,
)
from .disturbance import detect_open_data_disturbances, detect_traffic_disturbance, score_weather_context
from .decision import decide_action, suggestion_from_assessment
from .interfaces import RouteEvidence
from .road_traffic import assess_road_traffic
from .local_data import DEFAULT_DATA_DIR, collect_local_context, read_snapshot
from .logistics import RhineStatus, classify_rhine_high_water


def _component(name: str, status: str, severity: float | None, weight: float, evidence: list[str]) -> dict:
    points = round(weight * severity / 100, 1) if severity is not None else None
    return {"name": name, "status": status, "severity_0_to_100": severity,
            "weight_points": weight, "contributed_points": points, "evidence": evidence}


def _rhine_severity(level_cm: float | None, segment: str | None, status: str) -> float | None:
    if status == "unknown":
        return None
    if status == "no_high_water_trigger":
        return 0.0
    if status == "restricted":
        return 100.0
    if level_cm is None or segment is None:
        return None
    restriction = RHINE_RESTRICTION_CM[segment]
    return round(25.0 + 75.0 * (level_cm - RHINE_PRE_ALERT_CM) / (restriction - RHINE_PRE_ALERT_CM), 1)


def _format_age(age_minutes: float | None) -> str:
    if age_minutes is None:
        return "age unknown"
    if age_minutes >= 60:
        return f"{age_minutes / 60:.1f} h old"
    return f"{age_minutes:.1f} min old"


def _format_value(value: object) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def _weather_context_values(measurements: dict) -> list[str]:
    labels = {
        "gre000z0": ("global radiation", "W/m²"),
        "sre000z0": ("sunshine duration", "min"),
        "fu3010z0": ("mean wind", "km/h"),
        "dkl010z0": ("wind direction", "°"),
        "ure200s0": ("relative humidity", "%"),
        "tde200s0": ("dew point", "°C"),
    }
    return [f"{name} {measurements[key]} {unit}" for key, (name, unit) in labels.items()
            if measurements.get(key) is not None]


def assess_observed_data(
    data_dir: Path = DEFAULT_DATA_DIR,
    route: RouteEvidence | None = None,
    route_segment: str | None = None,
    weather_snapshot: dict | None = None,
    source_snapshots: dict[str, dict] | None = None,
) -> dict:
    """Return a current-data score; stale and route-unmatched inputs stay excluded."""
    route = route or RouteEvidence()
    if not isfinite(route.buffer_hours) or route.buffer_hours < 0:
        raise ValueError("buffer hours must be finite and non-negative")
    for timestamp in (route.estimated_arrival_at, route.material_needed_at):
        if timestamp is not None and (timestamp.tzinfo is None or timestamp.utcoffset() is None):
            raise ValueError("logistics timestamps must include a timezone")
    context = collect_local_context(data_dir, weather_snapshot, source_snapshots)
    weather = context.get("weather") or {}
    weather_signal = score_weather_context(weather.get("measurements") or {})
    weather_signal = {
        **weather_signal,
        "source_status": weather.get("source_status", "unknown"),
        "last_observation_severity": weather_signal["score"],
        "current_score_eligible": weather.get("source_status") == "observed" and route.exposed_handling is True,
    }
    if weather.get("source_status") != "observed":
        weather_signal["status"] = weather.get("source_status", "unknown")
        weather_signal["evidence"] = [f"Weather feed is {weather.get('source_status', 'unknown')}; last observation is context only and excluded from the current score."]

    if weather.get("source_status") == "observed" and route.exposed_handling is not True:
        weather_signal["status"] = "context only"
        weather_signal["evidence"] = ["No exposed shipment handling was confirmed; station weather is context only."]

    traffic_snapshot = (source_snapshots.get("basel_dataset_100006")
                        if source_snapshots is not None else read_snapshot(data_dir, "basel_dataset_100006"))
    traffic_finding = detect_traffic_disturbance(
        data_dir, route.traffic_counters, snapshot=traffic_snapshot,
        historical_records=(traffic_snapshot or {}).get("history_results") if source_snapshots is not None else None,
    )
    traffic_severity = None
    if traffic_finding.robust_z is not None:
        traffic_severity = min(100.0, max(0.0, traffic_finding.robust_z / TRAFFIC_ANOMALY_THRESHOLD * 100.0))

    road_snapshot = source_snapshots.get("opentransportdata_basel_region") if source_snapshots is not None else None
    road = assess_road_traffic(data_dir, route, snapshot=road_snapshot)
    known_traffic = [value for value in (traffic_severity, road.severity) if value is not None]
    traffic_severity = max(known_traffic) if known_traffic else None
    selected_traffic_missing = (
        (bool(route.traffic_counters) and traffic_finding.robust_z is None)
        or (bool(route.road_counters or route.road_events) and road.severity is None)
    )
    # Maximum fusion needs all selected inputs, except when a known signal
    # already reaches the maximum and missing evidence cannot increase it.
    if selected_traffic_missing and traffic_severity != 100:
        traffic_severity = None

    rhine = context.get("rhine") or {}
    port = rhine.get("port_basel_rheinhalle") or {}
    level = port.get("value")
    if level is not None:
        try:
            level = float(level)
        except (TypeError, ValueError):
            level = None
    port_is_fresh = rhine.get("source_status") == "observed snapshot"
    port_level_for_score = level if port_is_fresh else None
    rhine_status = (classify_rhine_high_water(port_level_for_score, route_segment) if port_is_fresh else
                    RhineStatus("unknown", route_segment, level,
                                f"{rhine.get('port_freshness_reason', 'Port measurement freshness is unknown')} Excluded from the current score."))

    components = [
        _component("weather", weather_signal["status"],
                   weather_signal["score"] if weather_signal["current_score_eligible"] else None,
                   OPEN_WEATHER_WEIGHT,
                   weather_signal["evidence"]),
        _component("traffic", "available" if traffic_severity is not None else "unknown", traffic_severity, OPEN_TRAFFIC_WEIGHT,
                   [traffic_finding.summary, *traffic_finding.evidence, *road.evidence, *road.omitted]),
        _component("rhine", rhine_status.status,
                   _rhine_severity(port_level_for_score, route_segment, rhine_status.status), OPEN_RHINE_WEIGHT,
                   [rhine_status.reason]),
    ]

    urgency_score = None
    urgency_status = "not supplied"
    if route.estimated_arrival_at is not None and route.material_needed_at is not None:
        slack = (route.material_needed_at - route.estimated_arrival_at).total_seconds() / 3600
        if route.buffer_hours == 0:
            urgency_score = 100.0 if slack < 0 else 0.0
        else:
            urgency_score = min(100.0, max(0.0, (route.buffer_hours - slack) / route.buffer_hours * 100))
        urgency_status = "available"
    components.append(_component("production_urgency", urgency_status, urgency_score,
                                 OPEN_URGENCY_WEIGHT,
                                 ["ETA and material need-by inputs are caller-supplied, not in the open-data feeds."]))

    known = [item for item in components if item["contributed_points"] is not None]
    score_weight_coverage = sum(item["weight_points"] for item in known)
    evidence_coverage = len(known) / len(components) * 100
    coverage = evidence_coverage
    score = round(sum(item["contributed_points"] for item in known), 1) if known else None
    matched_route = replace(
        route,
        route_restricted=route.route_restricted or road.restricted or rhine_status.status == "restricted",
        disruption_observed=True if road.disrupted or rhine_status.status == "pre_alert" else route.disruption_observed,
        road_traffic_severity=road.severity,
        evidence=(*route.evidence, *road.evidence),
        traffic_anomaly=traffic_finding.robust_z,
        traffic_route_matched=traffic_finding.robust_z is not None,
        weather_severity=weather_signal["score"] if weather_signal["current_score_eligible"] else None,
    )
    assessment = decide_action(None, matched_route, observed_only=True)
    system_suggestion = suggestion_from_assessment(assessment)
    action, reason = assessment.action, assessment.reason

    current_traffic = traffic_finding.__dict__
    traffic_snapshot = traffic_snapshot or {}
    traffic_rows = ((traffic_snapshot.get("data") or {}).get("results") or [])
    def record_time(record: dict) -> float:
        raw = record.get("datetimeto") or record.get("datetimefrom") or ""
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return float("-inf")
    newest_traffic = max(traffic_rows, key=record_time) if traffic_rows else None
    traffic_context = {**(context.get("traffic") or {}), "baseline_available": traffic_finding.robust_z is not None}
    considered_data = []
    omitted_data = []
    if components[0]["contributed_points"] is not None:
        used_weather = weather_signal["measurements"]
        considered_data.append(
            "Basel/Binningen weather used by score: "
            f"air temperature {used_weather['temperature_c']} °C, "
            f"rain {used_weather['precipitation_mm_10min']} mm/10 min, "
            f"wind gust {used_weather['gust_kmh']} km/h "
            f"({_format_age(weather.get('observation_age_minutes'))})."
        )
        present_context = _weather_context_values(weather.get("measurements") or {})
        omitted_data.append(
            "Weather context only (not scored without an exposed handling window): "
            + (", ".join(present_context) if present_context else "no additional values available")
            + "."
        )
    else:
        last_weather = weather_signal["measurements"]
        weather_values = (
            f"air temperature {last_weather['temperature_c']} °C, "
            f"rain {last_weather['precipitation_mm_10min']} mm/10 min, "
            f"wind gust {last_weather['gust_kmh']} km/h"
        )
        omitted_data.append(
            "Weather score omitted: last readings were "
            f"{weather_values} ({_format_age(weather.get('observation_age_minutes'))}); "
            + "; ".join(weather_signal["evidence"])
        )
        present_context = _weather_context_values(weather.get("measurements") or {})
        if present_context:
            omitted_data.append("Additional weather fields shown as context only, not scored: "
                                + ", ".join(present_context) + ".")

    if traffic_finding.robust_z is not None:
        considered_data.append(
            "Traffic anomaly: fresh count and same-counter baseline were scored "
            f"({traffic_context.get('latest_record_age_minutes', 'unknown')} min old)."
        )
    else:
        omitted_data.append(
            "Traffic: "
            + (traffic_finding.summary.rstrip(".") + "." if traffic_finding.summary else "no usable traffic evidence.")
            + (" A comparable baseline is also unavailable." if not traffic_context.get("baseline_available") else "")
        )

    considered_data.extend(road.evidence)
    omitted_data.extend(road.omitted)
    if selected_traffic_missing and traffic_severity is None:
        omitted_data.append("Combined traffic score remains unknown: an explicitly selected traffic source is unavailable.")
    if road.evidence and road.severity is None:
        omitted_data.append("OpenTransportData score omitted: some selected road evidence is unavailable.")

    if rhine_status.status != "unknown":
        considered_data.append(
            f"Port of Switzerland gauge: {level} cm, scored for ship leg {route_segment} "
            f"(measurement {_format_age(rhine.get('port_observation_age_minutes'))})."
        )
    else:
        rhine_gauge_note = (
            f"Port gauge reading {level} cm is fresh but excluded because no matching ship leg was supplied."
            if level is not None and port_is_fresh and route_segment is None
            else rhine_status.reason
        )
        omitted_data.append(f"Rhine route effect: {rhine_gauge_note}")
    basel_stadt_reading = rhine.get("basel_stadt_latest")
    if basel_stadt_reading:
        omitted_data.append(
            f"Basel-Stadt gauge ({basel_stadt_reading.get('pegelhoehe', 'unknown')} cm) and discharge "
            f"({basel_stadt_reading.get('abfluss', 'unknown')} m³/s) are context only; this score uses "
            "the Port gauge for a matched ship leg."
        )

    if urgency_score is not None:
        considered_data.append("Production urgency: supplied ETA and material need-by time were scored.")
    else:
        omitted_data.append("Production urgency: omitted because estimated arrival and material need-by times were not both supplied.")
    omitted_data.append("Package temperature: no shipment sensor history is available in observed-data mode.")

    evidence_groups = {
        "available": len(known),
        "total": len(components),
        "percent": round(evidence_coverage, 1),
        "groups": [item["name"] for item in components],
    }
    return {
        "mode": "observed data only; no package-temperature curve, route disruption, or ETA is simulated",
        "pipeline": ["Open data", "Disturbance detection", "Risk assessment", "Manufacturing decision", "Factory dashboard"],
        "action": {"recommendation": action, "reason": reason},
        "system_suggestion": system_suggestion,
        "manufacturing_priority_score": {
            "score": score,
            "minimum": round(score or 0.0, 1),
            "maximum": round(min(100.0, (score or 0.0) + 100 - score_weight_coverage), 1),
            "coverage_percent": round(coverage, 1),
            "evidence_coverage": evidence_groups,
            "score_weight_coverage_percent": round(score_weight_coverage, 1),
            "components": components,
            "interpretation": "Evidence coverage counts usable input groups out of four, independent of their score weights. Score-weight coverage separately reports the total weight represented by those groups. Missing/stale inputs are excluded, not treated as zero. Score is the known contribution; minimum/maximum bound missing component weights, not statistical uncertainty.",
        },
        "data_review": {"considered": considered_data, "omitted": omitted_data},
        "current_observations": {
            "road_traffic": {**road.context, "severity_0_to_100": road.severity,
                             "evidence": road.evidence, "omitted": road.omitted},
            "weather": weather,
            "weather_score_details": weather_signal,
                        "traffic": {**traffic_context, "latest_observation": newest_traffic,
                        "finding": current_traffic},
            "rhine": {**rhine, "shipment_segment": route_segment,
                      "finding": rhine_status.__dict__},
        },
        "detected_open_data_disturbances": [
            *detect_open_data_disturbances(
                data_dir, route.traffic_counters, route_segment, context,
                traffic_snapshot, traffic_snapshot.get("history_results"),
            ),
            {"source": "OpenTransportData road traffic",
             "status": "unknown" if road.severity is None else "detected" if road.severity > 0 else "no_anomaly",
             "summary": "Verified route evidence; severity is a policy index, not predicted delay.",
             "severity_0_to_100": road.severity, "evidence": road.evidence, "omitted": road.omitted,
             "action_effect": "Existing shipment ETA, handling and alternate-route checks apply."},
        ],
    }


def render_observed_summary(result: dict) -> str:
    """Show current observations and the observed-only score in a short terminal view."""
    observations = result["current_observations"]
    weather = observations["weather"] or {}
    measurements = weather.get("measurements") or {}
    traffic = observations["traffic"]
    rhine = observations["rhine"]
    port = rhine.get("port_basel_rheinhalle") or {}
    basel_gauge = rhine.get("basel_stadt_latest") or {}
    weather_measurements = weather.get("measurements") or {}
    traffic_row = traffic.get("latest_observation") or {}
    score = result["manufacturing_priority_score"]
    current_score = f"{score['score']:.1f}" if score["score"] is not None else "unknown"
    components = {item["name"]: item for item in score["components"]}
    if score["evidence_coverage"]["available"] == 0:
        refresh_note = "Refresh saved feeds with: python3 pythontest/api_requester.py --once"
    else:
        refresh_note = ""
    lines = [
        "CURRENT OPEN-DATA ASSESSMENT — no simulation",
        f"Weather ({weather.get('storage', 'unknown')}): {weather.get('source_status', 'unknown')} ({_format_age(weather.get('observation_age_minutes'))}); "
        f"{measurements.get('tre200s0', 'unknown')} °C, "
        f"{measurements.get('rre150z0', 'unknown')} mm/10 min rain, gust {measurements.get('fu3010z1', 'unknown')} km/h; "
        f"last-observation context severity {observations['weather_score_details']['last_observation_severity'] if observations['weather_score_details']['last_observation_severity'] is not None else 'unknown'}/100; "
        f"weather contribution {components['weather']['contributed_points'] if components['weather']['contributed_points'] is not None else 'not scored'}/"
        f"{components['weather']['weight_points']:g} points.",
        f"Traffic: {traffic.get('source_status', 'unknown')}; newest count "
        f"{traffic_row.get('total', 'unknown')} at {traffic_row.get('sitename', 'unknown')} "
        f"(pw {traffic_row.get('pw', 'unknown')}, delivery vans {traffic_row.get('lief', 'unknown')}, heavy vehicles {traffic_row.get('lw', 'unknown')}) is "
        f"{_format_age(traffic.get('latest_record_age_minutes'))}; "
        f"baseline available: {traffic.get('baseline_available', False)}; {'excluded' if not traffic.get('baseline_available') else 'scored'}.",
        f"Weather context-only fields: radiation {weather_measurements.get('gre000z0', 'unknown')} W/m², "
        f"sunshine {weather_measurements.get('sre000z0', 'unknown')} min, humidity {weather_measurements.get('ure200s0', 'unknown')}%, "
        f"dew point {weather_measurements.get('tde200s0', 'unknown')} °C, mean wind {weather_measurements.get('fu3010z0', 'unknown')} km/h, "
        f"direction {weather_measurements.get('dkl010z0', 'unknown')}°; "
        "not scored without a supported relationship/exposed transfer.",
        f"Rhine: Port gauge {port.get('value', 'unknown')} cm ({rhine.get('source_status', 'unknown')}, "
        f"measurement {_format_age(rhine.get('port_observation_age_minutes'))}, "
        f"page fetch {_format_age(rhine.get('port_snapshot_age_minutes'))}); "
        f"Basel-Stadt gauge {basel_gauge.get('pegelhoehe', 'unknown')} cm ({_format_age(rhine.get('basel_stadt_observation_age_minutes'))}) "
        f"and discharge {basel_gauge.get('abfluss', 'unknown')} m³/s; "
        f"ship leg {'supplied' if rhine.get('shipment_segment') else 'not supplied'}, so route effect {'scored' if components['rhine']['contributed_points'] is not None else 'excluded'}.",
        f"Production urgency: {components['production_urgency']['status']}.",
        f"Decision: {result['action']['recommendation'].replace('_', ' ').title()} — {result['action']['reason']}",
        f"Current Risk Score: {current_score}/100 (known contribution); "
        f"missing-evidence range {score['minimum']:g}–{score['maximum']:g}/100.",
        f"OpenTransportData: {len(observations['road_traffic']['current_readings'])} counter readings, "
        f"{len(observations['road_traffic']['traffic_situations'])} event candidates; "
        f"matched severity {observations['road_traffic']['severity_0_to_100'] if observations['road_traffic']['severity_0_to_100'] is not None else 'unknown'}/100.",
        f"Evidence coverage: {score['evidence_coverage']['available']}/{score['evidence_coverage']['total']} input groups ({score['coverage_percent']:.0f}%). "
        f"Score-weight coverage: {score['score_weight_coverage_percent']:.0f}/100 points.",
        f"System Suggestion: {result['system_suggestion']['suggestion']} — {result['system_suggestion']['reason']}",
        "DATA REVIEW — considered in calculation",
        *[f"- {item}" for item in result["data_review"]["considered"]],
        "DATA REVIEW — omitted or context only",
        *[f"- {item}" for item in result["data_review"]["omitted"]],
        "A score with low evidence coverage reflects only the known observations, not a complete shipment-risk estimate.",
    ]
    if refresh_note:
        lines.append(refresh_note)
    return "\n".join(lines)
