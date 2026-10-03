/** The backend implements GET /map with this JSON shape. Coordinates use WGS84.
 * Add optional fields without changing callers. Renames require coordinated changes.
 * Locations describe map context, never inferred risk or operational status.
 */
export interface MapLocation {
  id: string;
  name: string;
  category: "port" | "river" | "weather";
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
