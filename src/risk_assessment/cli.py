"""Run a deterministic local cold-chain assessment scenario."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path

from .decision import decide_action, parse_time
from .disturbance import detect_open_data_disturbances
from .interfaces import RouteEvidence
from .logistics import TrafficAnomaly, classify_rhine_high_water, traffic_volume_anomaly
from .local_data import DEFAULT_DATA_DIR, collect_local_context, read_snapshot
from .thermal import analyze_temperature_series, simulate_package_temperature, time_to_temperature_limit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("hot", "cold", "observed-weather", "rain", "traffic", "rhine",
                                                "buffer", "expedite", "reroute", "stale", "all"), default="hot")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--start-c", type=float, default=7.0)
    parser.add_argument("--ambient-c", type=float, help="Scenario ambient temperature; defaults by scenario")
    parser.add_argument("--duration-minutes", type=float, default=60.0)
    parser.add_argument("--tau-minutes", type=float, default=90.0, help="Illustrative package thermal time constant")
    parser.add_argument("--buffer-hours", type=float, default=4.0)
    parser.add_argument("--eta-at", help="Estimated receipt time, ISO-8601 with timezone")
    parser.add_argument("--needed-at", help="Material need-by time, ISO-8601 with timezone")
    parser.add_argument("--alternate-route-available", action="store_true")
    parser.add_argument("--rhine-route-segment", choices=("basel_mittlere_bruecke_birsfelden", "rheinfelden_kembs"))
    parser.add_argument("--port-water-level-cm", type=float)
    parser.add_argument("--traffic-count", type=float)
    parser.add_argument("--traffic-baseline", help="Comma-separated comparable counts for a local anomaly calculation")
    return parser


def run(args: argparse.Namespace) -> dict:
    context = collect_local_context(args.data_dir)
    weather = context.get("weather") or {}
    weather_readings = weather.get("measurements", {})
    weather_current = weather.get("source_status") == "observed"
    observed_air_c = weather_readings.get("tre200s0") if weather_current else None
    fallback_air_c = observed_air_c if observed_air_c is not None else 20.0
    defaults = {"hot": 40.0, "cold": -5.0, "observed-weather": fallback_air_c,
                "rain": 5.0, "traffic": 5.0, "rhine": 5.0,
                "buffer": 5.0, "expedite": 5.0,
                "reroute": 5.0, "stale": 5.0}
    ambient = args.ambient_c if args.ambient_c is not None else defaults[args.scenario]
    duration = timedelta(minutes=args.duration_minutes)
    tau = timedelta(minutes=args.tau_minutes)
    readings = [] if args.scenario == "stale" else simulate_package_temperature(args.start_c, ambient, duration, tau)
    thermal = analyze_temperature_series(readings)
    route_evidence = []
    restricted = False
    disruption: bool | None = None
    route_segment = args.rhine_route_segment
    rhine_status = None
    traffic_result = None
    if args.scenario == "rhine":
        water_level = args.port_water_level_cm
        if water_level is None:
            rhine_context = context.get("rhine") or {}
            reading = (rhine_context.get("port_basel_rheinhalle") or {}).get("value") \
                if rhine_context.get("source_status") == "observed snapshot" else None
            water_level = float(reading) if reading is not None else None
        rhine_status = classify_rhine_high_water(water_level, route_segment)
        restricted = rhine_status.status == "restricted"
        disruption = restricted
        route_evidence.append(rhine_status.reason)
    if args.scenario == "buffer":
        disruption = True
        route_evidence.append("SIMULATED: a route disruption is detected; this is not inferred from current traffic volume.")
    if args.scenario == "expedite":
        now = datetime.now(timezone.utc)
        args.eta_at = args.eta_at or (now + timedelta(hours=5)).isoformat()
        args.needed_at = args.needed_at or (now + timedelta(hours=6)).isoformat()
        route_evidence.append("SIMULATED ETA leaves one hour before the material is needed.")
    if args.scenario == "reroute":
        route_segment = route_segment or "basel_mittlere_bruecke_birsfelden"
        water_level = args.port_water_level_cm if args.port_water_level_cm is not None else 800.0
        rhine_status = classify_rhine_high_water(water_level, route_segment)
        restricted = rhine_status.status == "restricted"
        disruption = restricted
        args.alternate_route_available = True
        route_evidence.append("SIMULATED: high-water level and matching ship leg; not the live gauge value.")
        route_evidence.append(rhine_status.reason)
    if args.scenario == "traffic":
        baseline = [float(value.strip()) for value in args.traffic_baseline.split(",") if value.strip()] if args.traffic_baseline else []
        count = args.traffic_count
        if count is None:
            traffic_snapshot = read_snapshot(args.data_dir, "basel_dataset_100006") or {}
            results = (traffic_snapshot.get("data") or {}).get("results") or [] \
                if context["traffic"]["source_status"] == "observed snapshot" else []
            count = float(results[0].get("total", 0)) if results else 0.0
        if count is None or (args.traffic_count is None and not results):
            traffic_result = TrafficAnomaly("unknown", None, None, "No traffic count is available in the local snapshot.")
        else:
            traffic_result = traffic_volume_anomaly(count, baseline)
        route_evidence.append(traffic_result.reason)
    if args.scenario == "rain":
        route_evidence.append("Rain is handling context only; no tracked exposed stop or route delay was provided.")
    if args.scenario == "stale":
        thermal = analyze_temperature_series([])
        route_evidence.append("Sensor history intentionally missing in this scenario.")
    route = RouteEvidence(disruption_observed=disruption, route_restricted=restricted,
                          alternate_route_available=args.alternate_route_available,
                          traffic_anomaly=traffic_result.robust_z if traffic_result else None,
                          estimated_arrival_at=parse_time(args.eta_at),
                          material_needed_at=parse_time(args.needed_at),
                          buffer_hours=args.buffer_hours, evidence=tuple(route_evidence))
    assessment = decide_action(thermal, route)
    upper = time_to_temperature_limit(args.start_c, ambient, 8.0, tau)
    lower = time_to_temperature_limit(args.start_c, ambient, 2.0, tau)
    return {
        "mode": "illustrative deterministic scenario; not observed shipment telemetry",
        "pipeline": ["Open data", "Disturbance detection", "Risk assessment", "Manufacturing decision", "Factory dashboard"],
        "scenario": args.scenario,
        "scenario_inputs": {"start_temperature_c": args.start_c, "ambient_temperature_c": ambient,
                            "duration_minutes": args.duration_minutes, "time_constant_minutes": args.tau_minutes,
                            "temperature_limits_c": [2, 8],
                            "ambient_source": "MeteoSwiss observation" if args.ambient_c is None and observed_air_c is not None
                            and args.scenario not in ("hot", "cold", "stale") else "illustrative scenario assumption"},
        "package_temperature": {"samples": len(readings), "final_temperature_c": readings[-1].temperature_c if readings else None,
                                "minutes_above_8": thermal.minutes_above_max, "minutes_below_2": thermal.minutes_below_min,
                                "peak_above_8_c": thermal.peak_above_max_c, "peak_below_2_c": thermal.peak_below_min_c,
                                "hot_degree_hours": thermal.hot_degree_hours, "cold_degree_hours": thermal.cold_degree_hours,
                                "sensor_accuracy_unknown": thermal.sensor_accuracy_unknown,
                                "quality_review_required": thermal.quality_review_required,
                                "evidence": list(thermal.evidence),
                                "time_to_8_minutes_at_constant_ambient": upper,
                                "time_to_2_minutes_at_constant_ambient": lower},
        "assessment": {"action": assessment.action, "reason": assessment.reason,
                       "thermal_status": assessment.thermal_status, "logistics_status": assessment.logistics_status,
                       "logistics_evidence": list(assessment.logistics_evidence)},
        "traffic_anomaly": traffic_result.__dict__ if traffic_result else None,
        "rhine_status": rhine_status.__dict__ if rhine_status else None,
        "detected_open_data_disturbances": detect_open_data_disturbances(args.data_dir),
        "local_observed_context": context,
        "limitations": ["Scenario package temperatures are simulated, not measured.",
                        "Saved weather is a regional observation, not a shipment forecast or box reading.",
                        "The saved ten-record traffic sample has no baseline and cannot establish congestion.",
                        "Local Rhine gauge snapshots do not create a route restriction without a matching ship-leg segment.",
                        "No product-specific stability rule is available; quality review is not a damage/safety verdict."],
    }


def run_demo_suite(args: argparse.Namespace) -> str:
    """Show all four decision paths beside the current local-data assessment."""
    now = datetime.now(timezone.utc)
    specifications = [
        ("Normal", "observed-weather", now + timedelta(hours=2), now + timedelta(hours=8)),
        ("Buffer", "buffer", now + timedelta(hours=2), now + timedelta(hours=8)),
        ("Expedite", "expedite", now + timedelta(hours=5), now + timedelta(hours=6)),
        ("Reroute", "reroute", now + timedelta(hours=2), now + timedelta(hours=8)),
    ]
    outcomes = []
    for label, scenario, eta, need_by in specifications:
        case = copy.copy(args)
        case.scenario = scenario
        case.start_c = 5.0
        case.ambient_c = 5.0
        case.duration_minutes = 10.0
        case.eta_at = eta.isoformat()
        case.needed_at = need_by.isoformat()
        outcome = run(case)
        outcomes.append((label, outcome))

    context = outcomes[0][1]["local_observed_context"]
    disturbances = outcomes[0][1]["detected_open_data_disturbances"]
    weather = context.get("weather") or {}
    measurements = weather.get("measurements") or {}
    traffic = context.get("traffic") or {}
    rhine = context.get("rhine") or {}
    lines = [
        "FACTORY DASHBOARD — local scenario demo",
        "Open data → Disturbance detection → Risk assessment → Manufacturing decision → Dashboard",
        "",
        "LIVE LOCAL INPUTS",
        f"- Weather: {weather.get('source_status', 'unknown')}; BAS air temperature {measurements.get('tre200s0', 'unknown')} °C.",
        f"- Traffic: {traffic.get('source_status', 'unknown')}; {traffic.get('record_count', 0)} rows; baseline available: {traffic.get('baseline_available', False)}.",
        f"- Rhine: {rhine.get('source_status', 'unknown')}; Port gauge {((rhine.get('port_basel_rheinhalle') or {}).get('value', 'unknown'))} cm.",
        "",
        "OPEN-DATA DISTURBANCE DETECTION",
    ]
    lines.extend(f"- {item['source']}: {item['status']} — {item['summary']}" for item in disturbances)
    lines.extend([
        "",
        "DECISION SCENARIOS (package starts and stays at simulated 5 °C)",
        "| Case | Result | Route/ETA evidence |",
        "|---|---|---|",
    ])
    for label, outcome in outcomes:
        assessment = outcome["assessment"]
        evidence = "; ".join(assessment["logistics_evidence"]) or "No route trigger"
        lines.append(f"| {label} | **{assessment['action'].replace('_', ' ').title()}** | {evidence} |")
    lines.extend([
        "",
        "The four decision triggers are simulated so each pathway can be checked without GPS or a map. Current open data stays visible as real context; it does not silently become a simulated truck delay.",
        "Traffic counts can detect unusual volume only when fresh, route-matched counts have enough same-counter/day/hour history. A volume anomaly by itself is not congestion; measured ETA/slack is what drives Expedite.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    if args.scenario == "all":
        try:
            print(run_demo_suite(args))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise SystemExit(str(exc)) from exc
        return 0
    if (not all(isfinite(value) for value in (args.start_c, args.duration_minutes, args.tau_minutes, args.buffer_hours))
            or (args.ambient_c is not None and not isfinite(args.ambient_c))
            or args.duration_minutes <= 0 or args.tau_minutes <= 0 or args.buffer_hours < 0):
        raise SystemExit("duration and time constant must be positive; buffer cannot be negative")
    try:
        result = run(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
