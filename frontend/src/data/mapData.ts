import type { MapDataSource, MapSnapshot } from "../interfaces";

export const demoSnapshot: MapSnapshot = {
  mode: "demo",
  updatedAt: null,
  locations: [
    {
      id: "port",
      name: "Hafen Kleinhüningen",
      category: "port",
      latitude: 47.5855,
      longitude: 7.5922,
      description:
        "Orientierungspunkt für den Gütertransport auf dem Rhein. Später lassen sich hier Logistikdaten anzeigen.",
    },
    {
      id: "rhine",
      name: "Rhein · Mittlere Brücke",
      category: "river",
      latitude: 47.5618,
      longitude: 7.5895,
      description:
        "Der Rhein als Verbindung durch Basel. Vorgesehen für die spätere Einbindung von Pegel- und Abflussdaten.",
    },
    {
      id: "weather",
      name: "Basel / Binningen",
      category: "weather",
      latitude: 47.5411,
      longitude: 7.5836,
      description:
        "Orientierungspunkt für den Wetterkontext der Region. Aktuelle Messwerte werden noch nicht angezeigt.",
    },
  ],
};

/** Validate external JSON before it reaches the map or the UI. */
export function parseSnapshot(value: unknown): MapSnapshot {
  if (!value || typeof value !== "object")
    throw new Error("Ungültige Kartendaten.");
  const snapshot = value as MapSnapshot;
  if (
    !["demo", "live"].includes(snapshot.mode) ||
    !Array.isArray(snapshot.locations) ||
    !(
      snapshot.updatedAt === null ||
      (typeof snapshot.updatedAt === "string" &&
        Number.isFinite(Date.parse(snapshot.updatedAt)))
    )
  ) {
    throw new Error("Ungültiges Datenformat vom Backend.");
  }
  const ids = new Set<string>();
  for (const location of snapshot.locations) {
    if (
      !location ||
      typeof location.id !== "string" ||
      !location.id ||
      ids.has(location.id) ||
      typeof location.name !== "string" ||
      typeof location.description !== "string" ||
      !["port", "river", "weather", "traffic"].includes(location.category) ||
      !Number.isFinite(location.latitude) ||
      Math.abs(location.latitude) > 90 ||
      !Number.isFinite(location.longitude) ||
      Math.abs(location.longitude) > 180
    ) {
      throw new Error("Ungültiger Standort vom Backend.");
    }
    ids.add(location.id);
  }
  return snapshot;
}

export function createMapDataSource(baseUrl?: string): MapDataSource {
  return {
    async load(signal) {
      if (!baseUrl) return demoSnapshot;
      const response = await fetch(`${baseUrl.replace(/\/$/, "")}/map`, {
        signal,
      });
      if (!response.ok)
        throw new Error(
          `Kartendaten konnten nicht geladen werden (HTTP ${response.status}).`,
        );
      return parseSnapshot(await response.json());
    },
  };
}

export const mapDataSource = createMapDataSource(
  import.meta.env.VITE_API_BASE_URL,
);
