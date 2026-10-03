"""Assess saved open data by default, or explicitly run a local scenario."""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path

from .decision import decide_action, parse_time, suggestion_from_assessment
from .config import ROUTE_WEIGHT, THERMAL_WEIGHT, URGENCY_WEIGHT
from .disturbance import detect_open_data_disturbances
from .interfaces import RoadCounterMatch, RoadEventMatch, RouteEvidence, TrafficCounterMatch
from .logistics import TrafficAnomaly, classify_rhine_high_water, traffic_volume_anomaly
from .local_data import DEFAULT_DATA_DIR, collect_local_context, read_snapshot
from .observed import assess_observed_data, render_observed_summary
from .priority import calculate_priority_score
from .thermal import analyze_temperature_series, simulate_package_temperature, time_to_temperature_limit


def parse_traffic_counters(values: list[str]) -> tuple[TrafficCounterMatch, ...]:
    """Parse explicitly configured route-counter mappings."""
    matches = []
    for value in values:
        parts = value.split("|")
        if len(parts) != 3 or not parts[0].strip() or not parts[1].strip():
            raise ValueError("traffic counter must be SITE|DIRECTION|LANE")
        matches.append(TrafficCounterMatch(parts[0].strip(), parts[1].strip(), int(parts[2])))
    return tuple(matches)


def parse_road_counters(values: list[str]) -> tuple[RoadCounterMatch, ...]:
    matches = []
    for value in values:
        parts = value.split("|")
        if len(parts) != 3 or not parts[0].strip() or parts[1] not in ("light", "heavy"):
            raise ValueError("road counter must be SITE_ID|light or heavy|NORMAL_SPEED_KMH")
        speed = float(parts[2])
        if not isfinite(speed) or speed <= 0:
            raise ValueError("road normal speed must be finite and positive")
        matches.append(RoadCounterMatch(parts[0].strip(), parts[1], speed))
    return tuple(matches)


def parse_road_events(values: list[str]) -> tuple[RoadEventMatch, ...]:
    matches = []
    for value in values:
        parts = value.split("|")
        if len(parts) != 3 or not parts[0].strip() or parts[1] not in ("disrupted", "restricted"):
            raise ValueError("road event must be ID|disrupted or restricted|SOURCE_UPDATED_AT")
        parse_time(parts[2])
        matches.append(RoadEventMatch(parts[0].strip(), parts[1], parts[2]))
    return tuple(matches)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("observed", "hot", "cold", "normal", "observed-weather", "combined", "rain", "traffic", "rhine",
                                                "buffer", "expedite", "reroute", "stale", "all"), default="observed",
                        help="Default: score saved observations only. Other scenarios explicitly simulate inputs.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-format", choices=("table", "json"), default="table",
                        help="Use a readable terminal summary (default) or machine-readable JSON")
    parser.add_argument("--start-c", type=float, default=7.0)
    parser.add_argument("--ambient-c", type=float, help="Scenario ambient temperature; defaults by scenario")
    parser.add_argument("--duration-minutes", type=float, default=60.0)
    parser.add_argument("--tau-minutes", type=float, default=90.0, help="Illustrative package thermal time constant")
    parser.add_argument("--buffer-hours", type=float, default=4.0)
    parser.add_argument("--eta-at", help="Estimated receipt time, ISO-8601 with timezone")
    parser.add_argument("--needed-at", help="Material need-by time, ISO-8601 with timezone")
    parser.add_argument("--alternate-route-available", action="store_true")
    parser.add_argument("--route-status", choices=("clear", "disrupted", "unknown"),
                        help="Explicit shipment-route status; absence remains unknown")
    parser.add_argument("--alternate-route-suitable", action="store_true", help="Alternative verified for refrigerated material handling")
    parser.add_argument("--alternate-eta-at", help="Alternative arrival, ISO-8601 with timezone")
    handling = parser.add_mutually_exclusive_group()
    handling.add_argument("--exposed-handling", dest="exposed_handling", action="store_const", const=True)
    handling.add_argument("--controlled-handling", dest="exposed_handling", action="store_const", const=False)
    parser.add_argument("--traffic-counter", action="append", default=[], metavar="SITE|DIRECTION|LANE",
                        help="Route-matched counter; repeat for multiple lanes")
    parser.add_argument("--road-counter", action="append", default=[], metavar="ID|CLASS|NORMAL_KMH",
                        help="Verified remaining-route detector; class light/heavy and comparable normal speed. Observed mode only.")
    parser.add_argument("--road-event", action="append", default=[], metavar="ID|EFFECT|UPDATED_AT",
                        help="Verified event direction/vehicle applicability, effect disrupted/restricted, exact source version time. Observed mode only.")
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
    defaults = {"hot": 40.0, "cold": -5.0, "normal": 5.0, "observed-weather": fallback_air_c, "combined": fallback_air_c,
                "rain": 5.0, "traffic": 5.0, "rhine": 5.0,
                "buffer": 5.0, "expedite": 5.0,
                "reroute": 5.0, "stale": 5.0}
    ambient = args.ambient_c if args.ambient_c is not None else defaults[args.scenario]
    duration = timedelta(minutes=args.duration_minutes)
    tau = timedelta(minutes=args.tau_minutes)
    readings = [] if args.scenario == "stale" else simulate_package_temperature(args.start_c, ambient, duration, tau)
    thermal = analyze_temperature_series(
        readings,
        monitoring_started_at=readings[0].observed_at if readings else None,
        evaluated_at=readings[-1].observed_at if readings else None,
    )
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
    if args.scenario == "combined":
        disruption = True
        now = datetime.now(timezone.utc)
        args.eta_at = args.eta_at or (now + timedelta(hours=5)).isoformat()
        args.needed_at = args.needed_at or (now + timedelta(hours=6)).isoformat()
        route_evidence.append("SIMULATED: traffic disruption and one hour of production slack; not inferred from live traffic counts.")
    if args.scenario in ("normal", "expedite"):
        disruption = False
        if args.scenario == "normal":
            route_evidence.append("SIMULATED baseline case: no route disruption is supplied.")
    if args.scenario == "reroute":
        route_segment = route_segment or "basel_mittlere_bruecke_birsfelden"
        water_level = args.port_water_level_cm if args.port_water_level_cm is not None else 800.0
        rhine_status = classify_rhine_high_water(water_level, route_segment)
        restricted = rhine_status.status == "restricted"
        disruption = restricted
        args.alternate_route_available = True
        args.alternate_route_suitable = True
        now = datetime.now(timezone.utc)
        args.eta_at = args.eta_at or (now + timedelta(hours=2)).isoformat()
        args.needed_at = args.needed_at or (now + timedelta(hours=8)).isoformat()
        args.alternate_eta_at = (parse_time(args.eta_at) - timedelta(minutes=30)).isoformat()
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
    if args.route_status is not None:
        disruption = {"clear": False, "disrupted": True, "unknown": None}[args.route_status]
    route = RouteEvidence(disruption_observed=disruption, route_restricted=restricted,
                          alternate_route_available=args.alternate_route_available,
                          traffic_anomaly=traffic_result.robust_z if traffic_result else None,
                          estimated_arrival_at=parse_time(args.eta_at),
                          material_needed_at=parse_time(args.needed_at),
                          buffer_hours=args.buffer_hours, evidence=tuple(route_evidence),
                          exposed_handling=args.exposed_handling,
                          traffic_route_matched=bool(args.traffic_counter),
                          traffic_counters=parse_traffic_counters(args.traffic_counter),
                          alternate_route_suitable=args.alternate_route_suitable,
                          alternate_arrival_at=parse_time(args.alternate_eta_at))
    assessment = decide_action(thermal, route)
    priority = calculate_priority_score(thermal, route)
    suggestion = suggestion_from_assessment(assessment)
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
                            and args.scenario in ("observed-weather", "combined") else "illustrative scenario assumption"},
        "package_temperature": {"samples": len(readings), "final_temperature_c": readings[-1].temperature_c if readings else None,
                                "minutes_above_8": thermal.minutes_above_max, "minutes_below_2": thermal.minutes_below_min,
                                "peak_above_8_c": thermal.peak_above_max_c, "peak_below_2_c": thermal.peak_below_min_c,
                                "hot_degree_hours": thermal.hot_degree_hours, "cold_degree_hours": thermal.cold_degree_hours,
                                "sensor_accuracy_unknown": thermal.sensor_accuracy_unknown,
                                "incomplete_history": thermal.incomplete_history,
                                "quality_review_required": thermal.quality_review_required,
                                "evidence": list(thermal.evidence),
                                "time_to_8_minutes_at_constant_ambient": upper,
                                "time_to_2_minutes_at_constant_ambient": lower},
        "assessment": {"action": assessment.action, "reason": assessment.reason,
                       "thermal_status": assessment.thermal_status, "logistics_status": assessment.logistics_status,
                       "logistics_evidence": list(assessment.logistics_evidence)},
        "manufacturing_priority_score": priority.as_dict(),
        "system_suggestion": suggestion,
        "traffic_anomaly": traffic_result.__dict__ if traffic_result else None,
        "rhine_status": rhine_status.__dict__ if rhine_status else None,
        "detected_open_data_disturbances": detect_open_data_disturbances(args.data_dir),
        "local_observed_context": context,
        "limitations": ["Scenario package temperatures are simulated, not measured.",
                        "The priority score is a configurable prototype index, not a calibrated probability or product-quality verdict.",
                        "The score weights are illustrative; use shipment outcomes and factory review to calibrate them before operational use.",
                        "Saved weather is a regional observation, not a shipment forecast or box reading.",
                        "The saved ten-record traffic sample has no baseline and cannot establish congestion.",
                        "Local Rhine gauge snapshots do not create a route restriction without a matching ship-leg segment.",
                        "No product-specific stability rule is available; quality review is not a damage/safety verdict."],
    }


def run_demo_suite_data(args: argparse.Namespace) -> dict:
    """Return structured scenario results suitable for later dashboard use."""
    now = datetime.now(timezone.utc)
    specifications = [
        ("Normal", "normal", now + timedelta(hours=2), now + timedelta(hours=8)),
        ("Buffer", "buffer", now + timedelta(hours=2), now + timedelta(hours=8)),
        ("Expedite", "expedite", now + timedelta(hours=5), now + timedelta(hours=6)),
        ("Reroute", "reroute", now + timedelta(hours=2), now + timedelta(hours=8)),
        ("Combined weather + traffic + deadline", "combined", None, None),
    ]
    outcomes = []
    for label, scenario, eta, need_by in specifications:
        case = copy.copy(args)
        case.scenario = scenario
        case.start_c = 7.0 if scenario == "combined" else 5.0
        case.ambient_c = None if scenario == "combined" else 5.0
        case.duration_minutes = 30.0 if scenario == "combined" else 10.0
        case.exposed_handling = scenario == "combined"
        case.eta_at = eta.isoformat() if eta else None
        case.needed_at = need_by.isoformat() if need_by else None
        outcome = run(case)
        outcomes.append((label, outcome))

    context = outcomes[0][1]["local_observed_context"]
    disturbances = outcomes[0][1]["detected_open_data_disturbances"]
    return {
        "mode": "local observed context plus explicitly simulated scenario results",
        "pipeline": ["Open data", "Disturbance detection", "Risk assessment", "Manufacturing decision", "Factory dashboard"],
        "current_observed_assessment": run_observed(args),
        "local_observed_context": context,
        "detected_open_data_disturbances": disturbances,
        "scenarios": [
            {
                "label": label,
                "scenario": outcome["scenario"],
                "scenario_inputs": outcome["scenario_inputs"],
                "package_temperature": outcome["package_temperature"],
                "assessment": outcome["assessment"],
                "manufacturing_priority_score": outcome["manufacturing_priority_score"],
                "system_suggestion": outcome["system_suggestion"],
                "traffic_anomaly": outcome["traffic_anomaly"],
                "rhine_status": outcome["rhine_status"],
            }
            for label, outcome in outcomes
        ],
    }


def run_demo_suite(args: argparse.Namespace, results: dict | None = None) -> str:
    """Render all decision paths beside current local data for terminal review."""
    results = results or run_demo_suite_data(args)
    outcomes = [(item["label"], item) for item in results["scenarios"]]
    context = results["local_observed_context"]
    disturbances = results["detected_open_data_disturbances"]
    observed_score = results["current_observed_assessment"]["manufacturing_priority_score"]
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
        "CURRENT OBSERVED-DATA SCORE (no simulated inputs)",
        f"Current Risk Score: {observed_score['score'] if observed_score['score'] is not None else 'unknown'}/100 "
        f"(evidence coverage {observed_score['evidence_coverage']['available']}/{observed_score['evidence_coverage']['total']} groups; "
        f"weight coverage {observed_score['score_weight_coverage_percent']:.0f}/100)",
        f"System Suggestion: {results['current_observed_assessment']['system_suggestion']['suggestion']} — "
        f"{results['current_observed_assessment']['system_suggestion']['reason']}",
        "",
        "DECISION SCENARIOS (package readings and route/ETA cases are simulations)",
        "| Case | Result | System suggestion | Priority score | Evidence coverage | Weight coverage | Route/ETA evidence |",
        "|---|---|---|---:|---:|---:|---|",
    ])
    for label, outcome in outcomes:
        assessment = outcome["assessment"]
        priority = outcome["manufacturing_priority_score"]
        score = f"{priority['minimum']:.1f}" if priority["minimum"] == priority["maximum"] else f"{priority['minimum']:.1f}–{priority['maximum']:.1f}"
        evidence = "; ".join(assessment["logistics_evidence"]) or "No route trigger"
        lines.append(f"| {label} | **{assessment['action'].replace('_', ' ').title()}** | **{outcome['system_suggestion']['suggestion']}** | {score} | {priority['evidence_coverage_available']}/{priority['evidence_coverage_total']} ({priority['coverage_percent']:.0f}%) | {priority['score_weight_coverage_percent']:.0f}% | {evidence} |")
    combined = next(item for item in results["scenarios"] if item["scenario"] == "combined")
    combined_score = combined["manufacturing_priority_score"]
    combined_score_value = (f"{combined_score['minimum']:.1f}"
                            if combined_score["minimum"] == combined_score["maximum"]
                            else f"{combined_score['minimum']:.1f}–{combined_score['maximum']:.1f}")
    combined_ambient_label = ("observed MeteoSwiss air temperature" if combined["scenario_inputs"]["ambient_source"] == "MeteoSwiss observation"
                              else "illustrative 20 °C fallback ambient")
    lines.extend([
        "",
        "The Normal, Buffer, Expedite, and Reroute cases are simulated so each pathway can be checked without GPS or a map. Current open data stays visible as real context; it does not silently become a simulated truck delay.",
        "Traffic counts can detect unusual volume only when fresh, route-matched counts have enough same-counter/day/hour history. A volume anomaly by itself is not congestion; measured ETA/slack is what drives Expedite.",
        f"Priority score = {THERMAL_WEIGHT:.0%} package thermal exposure + {URGENCY_WEIGHT:.0%} production urgency + {ROUTE_WEIGHT:.0%} route disturbance. Component scales are 0–100; combined weighted points add, while missing inputs are shown as a score range rather than counted as zero.",
        "The combined case uses current outdoor temperature as a simulated ambient exposure, a simulated traffic disruption, and a simulated one-hour production slack. A quality review overrides logistics action if the simulated box temperature leaves 2–8 °C; the score itself never orders quarantine.",
        "A quality review/hold is triggered by package-temperature evidence and stays separate from the manufacturing priority score.",
        "",
        f"Combined Scenario Risk Score: {combined_score_value}/100 ({combined_ambient_label} + simulated package, traffic, and deadline)",
    ])
    return "\n".join(lines)


def render_scenario_summary(result: dict) -> str:
    """Show a simulated scenario's score and evidence in a readable terminal view."""
    score = result["manufacturing_priority_score"]
    low, high = score["minimum"], score["maximum"]
    score_text = f"{low:.1f}" if low == high else f"{low:.1f}–{high:.1f}"
    inputs = result["scenario_inputs"]
    package = result["package_temperature"]
    assessment = result["assessment"]
    lines = [
        f"SCENARIO: {result['scenario']} (simulated; not observed shipment telemetry)",
        f"Package temperature: {package['final_temperature_c']:.1f} °C after {inputs['duration_minutes']:.0f} min"
        if package["final_temperature_c"] is not None else "Package temperature: unavailable in this scenario",
        f"Decision: {assessment['action'].replace('_', ' ').title()} — {assessment['reason']}",
        f"Current Risk Score: {score_text}/100",
        f"Evidence coverage: {score['evidence_coverage_available']}/{score['evidence_coverage_total']} input groups ({score['coverage_percent']:.0f}%). "
        f"Score-weight coverage: {score['score_weight_coverage_percent']:.0f}/100 points.",
        f"System Suggestion: {result['system_suggestion']['suggestion']} — {result['system_suggestion']['reason']}",
        score["interpretation"],
    ]
    if assessment["logistics_evidence"]:
        lines.append("Scenario evidence: " + " ".join(assessment["logistics_evidence"]))
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    if (args.road_counter or args.road_event) and args.scenario not in ("observed", "all"):
        raise SystemExit("Road evidence options apply to observed assessment; use --scenario observed or all.")
    if args.scenario in ("observed", "all"):
        try:
            result = run_observed(args) if args.scenario == "observed" else run_demo_suite_data(args)
            output = (json.dumps(result, indent=2, ensure_ascii=False)
                      if args.output_format == "json" else
                      render_observed_summary(result) if args.scenario == "observed" else run_demo_suite(args, result))
            print(output)
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
    output = (json.dumps(result, indent=2, ensure_ascii=False)
              if args.output_format == "json" else render_scenario_summary(result))
    print(output)
    return 0


def run_observed(args: argparse.Namespace) -> dict:
    """Score currently saved public observations and optional caller ETA/route metadata."""
    route = RouteEvidence(
        disruption_observed={"clear": False, "disrupted": True, "unknown": None}.get(args.route_status),
        alternate_route_available=args.alternate_route_available,
        estimated_arrival_at=parse_time(args.eta_at),
        material_needed_at=parse_time(args.needed_at),
        buffer_hours=args.buffer_hours,
        exposed_handling=args.exposed_handling,
        traffic_counters=parse_traffic_counters(args.traffic_counter),
        road_counters=parse_road_counters(args.road_counter),
        road_events=parse_road_events(args.road_event),
        alternate_route_suitable=args.alternate_route_suitable,
        alternate_arrival_at=parse_time(args.alternate_eta_at),
    )
    return assess_observed_data(args.data_dir, route, args.rhine_route_segment)


if __name__ == "__main__":
    raise SystemExit(main())
