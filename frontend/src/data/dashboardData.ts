import type {
  DashboardSnapshot,
  FeedMode,
  DemoScenario,
  Coordinates,
} from "../interfaces";
import { parseSnapshot } from "./mapData";

const record = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === "object" && !Array.isArray(value);
const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);
const timestamp = (value: unknown): value is string =>
  typeof value === "string" && Number.isFinite(Date.parse(value));
const nullableTime = (value: unknown) => value === null || timestamp(value);
const between = (value: unknown, low: number, high: number) =>
  finite(value) && value >= low && value <= high;
const texts = (value: Record<string, unknown>, names: string[]) =>
  names.every((name) => typeof value[name] === "string");
const coordinates = (value: unknown): value is Coordinates[] =>
  Array.isArray(value) &&
  value.every(
    (point) =>
      Array.isArray(point) &&
      point.length === 2 &&
      between(point[0], -180, 180) &&
      between(point[1], -90, 90),
  );

/** Reject malformed/mixed-mode external responses before drawing routes or scores. */
export function parseDashboard(
  value: unknown,
  expectedMode?: FeedMode,
): DashboardSnapshot {
  parseSnapshot(value);
  if (
    !record(value) ||
    (expectedMode && value.mode !== expectedMode) ||
    !texts(value, ["sourceLabel", "transportSource"]) ||
    !Array.isArray(value.signals) ||
    !Array.isArray(value.alerts) ||
    !Array.isArray(value.shipments)
  ) {
    throw new Error("Ungültige Dashboard-Daten oder falscher Datenmodus.");
  }
  const ids = new Set<string>();
  for (const signal of value.signals) {
    if (
      !record(signal) ||
      !texts(signal, ["id", "title", "unit", "source", "detail"]) ||
      !(signal.value === null || finite(signal.value)) ||
      !nullableTime(signal.observedAt) ||
      !["current", "stale", "unknown"].includes(String(signal.freshness)) ||
      !["normal", "warning", "critical", "unknown"].includes(
        String(signal.severity),
      )
    )
      throw new Error("Ungültige Messdaten.");
  }
  for (const alert of value.alerts) {
    if (
      !record(alert) ||
      !texts(alert, ["id", "title", "detail"]) ||
      !["weather", "traffic"].includes(String(alert.kind)) ||
      !nullableTime(alert.observedAt) ||
      !["current", "stale", "unknown"].includes(String(alert.freshness))
    )
      throw new Error("Ungültige Verkehrsmeldung.");
  }
  for (const shipment of value.shipments) {
    if (
      !record(shipment) ||
      !texts(shipment, [
        "id",
        "name",
        "material",
        "origin",
        "destination",
        "routeName",
        "reason",
      ]) ||
      !shipment.id ||
      ids.has(String(shipment.id)) ||
      shipment.provenance !== "simulated" ||
      value.mode !== "demo" ||
      !["standard", "high", "critical"].includes(String(shipment.priority)) ||
      !["moving", "delayed", "delivered", "held"].includes(
        String(shipment.status),
      ) ||
      ![
        "normal",
        "buffer",
        "expedite",
        "reroute",
        "quality_review",
        "monitor",
      ].includes(String(shipment.action)) ||
      !coordinates(shipment.route) ||
      shipment.route.length < 2 ||
      !coordinates(shipment.alternativeRoute) ||
      !between(shipment.progress, 0, 1) ||
      !finite(shipment.temperatureC) ||
      !record(shipment.temperatureBand) ||
      !finite(shipment.temperatureBand.minimumC) ||
      !finite(shipment.temperatureBand.maximumC) ||
      shipment.temperatureBand.minimumC >= shipment.temperatureBand.maximumC ||
      !["departureAt", "etaAt", "neededAt", "observedAt"].every((key) =>
        timestamp(shipment[key]),
      ) ||
      !nullableTime(shipment.alternateEtaAt) ||
      !["distanceKm", "remainingKm", "delayMinutes", "bufferHours"].every(
        (key) => finite(shipment[key]) && Number(shipment[key]) >= 0,
      ) ||
      !finite(shipment.slackMinutes) ||
      !Array.isArray(shipment.temperatureHistory) ||
      shipment.temperatureHistory.length < 2 ||
      !shipment.temperatureHistory.every(
        (point) => record(point) && timestamp(point.at) && finite(point.value),
      ) ||
      !record(shipment.thermal) ||
      typeof shipment.thermal.quality_review_required !== "boolean" ||
      typeof shipment.thermal.incomplete_history !== "boolean" ||
      ![
        "minutes_above_max",
        "minutes_below_min",
        "hot_degree_hours",
        "cold_degree_hours",
      ].every((key) =>
        finite(
          shipment.thermal &&
            (shipment.thermal as Record<string, unknown>)[key],
        ),
      )
    ) {
      throw new Error("Ungültige Transportdaten.");
    }
    ids.add(String(shipment.id));
    const score = shipment.score;
    if (
      !record(score) ||
      !between(score.minimum, 0, 100) ||
      !between(score.maximum, Number(score.minimum), 100) ||
      !between(score.coverage_percent, 0, 100) ||
      !between(score.score_weight_coverage_percent, 0, 100) ||
      !between(
        score.evidence_coverage_available,
        0,
        Number(score.evidence_coverage_total),
      ) ||
      !finite(score.evidence_coverage_total) ||
      typeof score.interpretation !== "string" ||
      !record(score.components) ||
      !record(score.weighted_points) ||
      !["thermal", "route", "urgency"].every(
        (key) =>
          (score.components as Record<string, unknown>)[key] === null ||
          between((score.components as Record<string, unknown>)[key], 0, 100),
      ) ||
      !["thermal", "route", "urgency"].every(
        (key) =>
          (score.weighted_points as Record<string, unknown>)[key] === null ||
          between(
            (score.weighted_points as Record<string, unknown>)[key],
            0,
            100,
          ),
      )
    ) {
      throw new Error("Ungültige Bewertung.");
    }
  }
  if (
    value.mode === "live"
      ? value.simulation !== null || value.shipments.length > 0
      : !record(value.simulation) ||
        !["fleet", "normal", "traffic", "urgent", "heat", "reroute"].includes(
          String(value.simulation.scenario),
        ) ||
        !between(value.simulation.elapsedMinutes, 0, 180) ||
        !between(value.simulation.maximumMinutes, 0, 180) ||
        !between(value.simulation.minutesPerSecond, 0, 60)
  ) {
    throw new Error("Ungültige Simulationsdaten.");
  }
  return value as unknown as DashboardSnapshot;
}

export async function loadDashboard(
  mode: FeedMode,
  scenario: DemoScenario,
  elapsedMinutes: number,
  anchor: string,
  signal?: AbortSignal,
): Promise<DashboardSnapshot> {
  const base = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
  const query = new URLSearchParams({ mode });
  if (mode === "demo") {
    query.set("scenario", scenario);
    query.set("elapsedMinutes", String(elapsedMinutes));
    query.set("anchor", anchor);
  }
  const response = await fetch(`${base}/dashboard?${query}`, { signal });
  if (!response.ok) {
    throw new Error(
      mode === "live"
        ? "Live-Daten nicht erreichbar. Backend und Supabase-Verbindung prüfen."
        : "Demo-Daten nicht erreichbar. Bitte den Dashboard-Server starten.",
    );
  }
  return parseDashboard(await response.json(), mode);
}
