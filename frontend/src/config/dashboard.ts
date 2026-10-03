import type { DemoScenario, ShipmentAction } from "../interfaces";

export const scenarioLabels: Record<DemoScenario, string> = {
  fleet: "Flottenübersicht",
  normal: "Normalbetrieb",
  traffic: "Stau mit Zeitpuffer",
  urgent: "Stau + dringende Lieferung",
  heat: "Temperaturabweichung",
  reroute: "Geeignete Alternativroute",
};

export const actionLabels: Record<ShipmentAction, string> = {
  normal: "Normal",
  buffer: "Buffer",
  expedite: "Expedite",
  reroute: "Reroute",
  quality_review: "Qualitätsprüfung",
  monitor: "Beobachten",
};

export const actionDescriptions: Record<ShipmentAction, string> = {
  normal: "Paketdaten, Route und Zeitpuffer zeigen keinen Eingriffsbedarf.",
  buffer:
    "Eine Routenstörung ist bekannt, aber es bleibt genügend Zeitpuffer. Kontrollierte Lagerung beibehalten.",
  expedite:
    "Die erwartete Ankunft lässt weniger Zeit als der geplante Produktionspuffer. Lieferung priorisieren und Beschleunigung prüfen.",
  reroute:
    "Eine als geeignet hinterlegte Alternative erreicht das Ziel früher und vor dem Bedarfstermin. Umleitung prüfen.",
  quality_review:
    "Die Pakettemperatur oder ihre Messhistorie erfordert Prüfung. Weitergabe und Produktion bis zur autorisierten Freigabe sperren.",
  monitor:
    "Für eine konkrete Transportmaßnahme fehlen bestätigte Angaben. Situation prüfen und weiter beobachten.",
};

export const priorityLabels = {
  standard: "Standard",
  high: "Hoch",
  critical: "Kritisch",
};
export const statusLabels = {
  moving: "Unterwegs",
  delayed: "Im Stau",
  delivered: "Angekommen",
  held: "Im Qualitätshold",
};
export const freshnessLabels = {
  current: "Aktuell",
  stale: "Veraltet",
  unknown: "Unbekannt",
};
export const DASHBOARD_POLL_MS = 1000;
export const LIVE_POLL_MS = 60000;
export const API_TIMEOUT_MS = 45000;
