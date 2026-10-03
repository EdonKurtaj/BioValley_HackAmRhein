import type { Shipment, FeedMode } from "../interfaces";
import {
  actionLabels,
  priorityLabels,
  statusLabels,
} from "../config/dashboard";
import { timeLabel } from "./ShipmentDetails";

export function TransportSidebar({
  shipments,
  selectedId,
  onSelect,
  filter,
  onFilter,
  mode,
  loading,
  transportSource,
}: {
  shipments: Shipment[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  filter: string;
  onFilter: (value: string) => void;
  mode: FeedMode;
  loading: boolean;
  transportSource?: string;
}) {
  const visible =
    filter === "attention"
      ? shipments.filter(
          (shipment) =>
            shipment.action !== "normal" && shipment.status !== "delivered",
        )
      : shipments;
  return (
    <aside className="transport-sidebar">
      <div className="sidebar-heading">
        <p className="eyebrow">TRANSPORTE</p>
        <h2>
          Aktuelle Fahrten{" "}
          <span>{shipments.length.toString().padStart(2, "0")}</span>
        </h2>
      </div>
      <div className="filters">
        <button
          className={filter === "all" ? "active" : ""}
          aria-pressed={filter === "all"}
          onClick={() => onFilter("all")}
        >
          Alle
        </button>
        <button
          className={filter === "attention" ? "active" : ""}
          aria-pressed={filter === "attention"}
          onClick={() => onFilter("attention")}
        >
          Handlungsbedarf
        </button>
      </div>
      <div className="transport-list">
        {visible.map((shipment) => (
          <button
            className={`transport-card ${selectedId === shipment.id ? "selected" : ""}`}
            aria-pressed={selectedId === shipment.id}
            key={shipment.id}
            onClick={() => onSelect(shipment.id)}
          >
            <div className="transport-card-heading">
              <strong>{shipment.id}</strong>
              <span className={`action-pill action-${shipment.action}`}>
                {shipment.status === "delivered"
                  ? "Angekommen"
                  : actionLabels[shipment.action]}
              </span>
            </div>
            <p>
              {shipment.origin} <span>→</span> {shipment.destination}
            </p>
            <div className="transport-meta">
              <span>{statusLabels[shipment.status]}</span>
              <span>{priorityLabels[shipment.priority]}</span>
            </div>
            <progress
              max="1"
              value={shipment.progress}
              aria-label={`Routenfortschritt ${shipment.id}`}
            />
            <div className="transport-meta">
              <span>ETA {timeLabel(shipment.etaAt)}</span>
              <span>{shipment.temperatureC.toFixed(1)} °C</span>
            </div>
          </button>
        ))}
        {visible.length === 0 && (
          <div className="empty-transports">
            <span>⌖</span>
            <strong>
              {loading
                ? "Transporte werden geladen …"
                : mode === "live"
                  ? "Kein GPS-Feed verbunden"
                  : "Keine Transporte in dieser Auswahl"}
            </strong>
            <p>
              {mode === "live"
                ? "Für bewegte LKW, Pakettemperatur und vollständige Risikobewertung zur Demo wechseln."
                : "Alle Fahrten bleiben unter „Alle“ auswählbar."}
            </p>
          </div>
        )}
      </div>
      <div className="data-note">
        <span className="note-icon">ⓘ</span>
        <div>
          <strong>{transportSource ?? "Transportdaten"}</strong>
          <p>
            {mode === "demo"
              ? "GPS, Pakettemperatur, Stau und Termine ersetzen fehlende reale Transportdaten nur für die Demo."
              : "Regionale Messungen ersetzen keine Transport- oder Produktsensordaten."}
          </p>
        </div>
      </div>
    </aside>
  );
}
