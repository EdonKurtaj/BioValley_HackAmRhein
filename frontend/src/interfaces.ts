/** The backend implements GET /map with this JSON shape. Coordinates use WGS84.
 * Add optional fields without changing callers. Renames require coordinated changes.
 * Locations describe map context, never inferred risk or operational status.
 */
export interface MapLocation {
  id: string;
  name: string;
  category: "port" | "river" | "weather" | "traffic";
  latitude: number;
  longitude: number;
  description: string;
}

export interface MapSnapshot {
  locations: MapLocation[];
  /** null means no observation timestamp is available. */
  updatedAt: string | null;
  mode: "demo" | "live";
}

/** Replace the adapter, not UI components, when connecting a backend. */
export interface MapDataSource {
  load(signal?: AbortSignal): Promise<MapSnapshot>;
}

export type FeedMode = "demo" | "live";
export type DemoScenario =
  "fleet" | "normal" | "traffic" | "urgent" | "heat" | "reroute" | "harsh";
export type ShipmentAction =
  "normal" | "buffer" | "expedite" | "reroute" | "quality_review" | "monitor";
export type Coordinates = [number, number];
export type Freshness = "current" | "stale" | "unknown";

/** GET /api/dashboard. Live never supplies synthetic shipment evidence. */
export interface EnvironmentalSignal {
  id: string;
  title: string;
  value: number | null;
  unit: string;
  observedAt: string | null;
  freshness: Freshness;
  severity: "normal" | "warning" | "critical" | "unknown";
  source: string;
  detail: string;
}

export interface RegionalAlert {
  id: string;
  title: string;
  detail: string;
  kind: "weather" | "traffic";
  observedAt: string | null;
  freshness: Freshness;
}

export interface ShipmentScore {
  minimum: number;
  maximum: number;
  coverage_percent: number;
  score_weight_coverage_percent: number;
  evidence_coverage_available: number;
  evidence_coverage_total: number;
  components: Record<"thermal" | "route" | "urgency", number | null>;
  weighted_points: Record<"thermal" | "route" | "urgency", number | null>;
  interpretation: string;
}

export interface Shipment {
  id: string;
  name: string;
  material: string;
  priority: "standard" | "high" | "critical";
  origin: string;
  destination: string;
  routeName: string;
  route: Coordinates[];
  alternativeRoute: Coordinates[];
  /** Cached road geometry; disruption and movement remain synthetic in Demo mode. */
  routing?: {
    source: string;
    cachedAt: string;
    rerouted: boolean;
    message: string;
    candidateCount: number;
    blockedLocation: Coordinates | null;
  };
  progress: number;
  distanceKm: number;
  remainingKm: number;
  departureAt: string;
  etaAt: string;
  neededAt: string;
  alternateEtaAt: string | null;
  temperatureC: number;
  temperatureBand: { minimumC: number; maximumC: number };
  temperatureHistory: { at: string; value: number }[];
  thermal: {
    minutes_above_max: number;
    minutes_below_min: number;
    hot_degree_hours: number;
    cold_degree_hours: number;
    quality_review_required: boolean;
    incomplete_history: boolean;
  };
  score: ShipmentScore;
  action: ShipmentAction;
  reason: string;
  status: "moving" | "delayed" | "delivered" | "held";
  delayMinutes: number;
  slackMinutes: number;
  bufferHours: number;
  observedAt: string;
  provenance: "simulated";
}

export interface DashboardSnapshot extends MapSnapshot {
  signals: EnvironmentalSignal[];
  alerts: RegionalAlert[];
  shipments: Shipment[];
  sourceLabel: string;
  transportSource: string;
  simulation: null | {
    scenario: DemoScenario;
    elapsedMinutes: number;
    minutesPerSecond: number;
    maximumMinutes: number;
  };
}
