"""Run a deterministic local cold-chain assessment scenario."""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from math import isfinite
from pathlib import Path

from .decision import decide_action, parse_time
from .interfaces import RouteEvidence
from .logistics import TrafficAnomaly, classify_rhine_high_water, traffic_volume_anomaly
from .local_data import DEFAULT_DATA_DIR, collect_local_context, read_snapshot
from .thermal import analyze_temperature_series, simulate_package_temperature, time_to_temperature_limit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("hot", "cold", "observed-weather", "rain", "traffic", "rhine", "stale"), default="hot")
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
                "rain": fallback_air_c, "traffic": fallback_air_c, "rhine": fallback_air_c,
                "stale": fallback_air_c}
    ambient = args.ambient_c if args.ambient_c is not None else defaults[args.scenario]
    duration = timedelta(minutes=args.duration_minutes)
    tau = timedelta(minutes=args.tau_minutes)
    readings = simulate_package_temperature(args.start_c, ambient, duration, tau)
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
        "scenario": args.scenario,
        "scenario_inputs": {"start_temperature_c": args.start_c, "ambient_temperature_c": ambient,
                            "duration_minutes": args.duration_minutes, "time_constant_minutes": args.tau_minutes,
                            "temperature_limits_c": [2, 8],
                            "ambient_source": "MeteoSwiss observation" if args.ambient_c is None and observed_air_c is not None
                            and args.scenario not in ("hot", "cold", "stale") else "illustrative scenario assumption"},
        "package_temperature": {"samples": len(readings), "final_temperature_c": readings[-1].temperature_c,
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
        "local_observed_context": context,
        "limitations": ["Scenario package temperatures are simulated, not measured.",
                        "Saved weather is a regional observation, not a shipment forecast or box reading.",
                        "The saved ten-record traffic sample has no baseline and cannot establish congestion.",
                        "Local Rhine gauge snapshots do not create a route restriction without a matching ship-leg segment.",
                        "No product-specific stability rule is available; quality review is not a damage/safety verdict."],
    }


def main() -> int:
    args = build_parser().parse_args()
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
