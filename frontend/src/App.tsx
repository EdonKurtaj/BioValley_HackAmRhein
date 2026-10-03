import { useEffect, useState } from "react";
import { BaselMap } from "./components/BaselMap";
import { categories } from "./config/map";
import { mapDataSource } from "./data/mapData";
import type { MapLocation, MapSnapshot } from "./interfaces";

const emptyLocations: MapLocation[] = [];

export default function App() {
  const [snapshot, setSnapshot] = useState<MapSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [resetKey, setResetKey] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 12000);
    let active = true;
    setLoading(true);
    setError("");
    mapDataSource
      .load(controller.signal)
      .then((data) => {
        if (active) setSnapshot(data);
      })
      .catch((reason) => {
        if (active)
          setError(
            reason.name === "AbortError"
              ? "Die Datenquelle antwortet nicht. Bitte erneut versuchen."
              : reason.message || "Datenquelle nicht erreichbar.",
          );
      })
      .finally(() => {
        window.clearTimeout(timeout);
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [attempt]);
  const locations = snapshot?.locations ?? emptyLocations;
  const visible =
    filter === "all"
      ? locations
      : locations.filter((location) => location.category === filter);
  const selected = locations.find((location) => location.id === selectedId);

  return (
    <div className="app-shell">
      <header className="header">
        <a className="brand" href="/" aria-label="BioValley Startseite">
          <span className="brand-icon">
            b<span>v</span>
          </span>
          <span>
            BioValley<small>REGIONAL INTELLIGENCE</small>
          </span>
        </a>
        <span className="header-section">
          Region Basel <span className="slash">/</span> Übersicht
        </span>
        <span className="prototype">
          <i />
          Prototyp
        </span>
      </header>
      <main>
        <div className="page-heading">
          <div>
            <p className="eyebrow">DIE REGION IM BLICK</p>
            <h1>Basel. Alles auf einer Karte.</h1>
            <p className="subtitle">
              Rhein, Logistik und Wetter – der Ausgangspunkt für eure regionale
              Übersicht.
            </p>
          </div>
          <span className="region-tag">
            CH <span>Basel & Umgebung</span>
          </span>
        </div>
        <div className="workspace">
          <aside className="sidebar">
            <div className="sidebar-heading">
              <p className="eyebrow">ENTDECKEN</p>
              <h2>
                Standorte{" "}
                <span>{locations.length.toString().padStart(2, "0")}</span>
              </h2>
              <p>Wähle einen Standort für mehr Kontext.</p>
            </div>
            <div className="filters" aria-label="Standorte filtern">
              {[
                ["all", "Alle"],
                ...Object.entries(categories).map(([key, value]) => [
                  key,
                  value.label,
                ]),
              ].map(([key, label]) => (
                <button
                  key={key}
                  aria-pressed={filter === key}
                  className={filter === key ? "active" : ""}
                  onClick={() => {
                    setFilter(key);
                    setSelectedId(null);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="location-list" aria-live="polite">
              {loading ? (
                <p className="state-message">Standorte werden geladen …</p>
              ) : error ? (
                <div className="state-message" role="alert">
                  <p>{error}</p>
                  <button
                    className="text-button"
                    onClick={() => setAttempt(attempt + 1)}
                  >
                    Erneut versuchen ↗
                  </button>
                </div>
              ) : visible.length === 0 ? (
                <p className="state-message">
                  Keine Standorte in dieser Auswahl.
                </p>
              ) : (
                visible.map((location) => (
                  <button
                    key={location.id}
                    className={`location-card ${selectedId === location.id ? "selected" : ""}`}
                    aria-pressed={selectedId === location.id}
                    onClick={() => setSelectedId(location.id)}
                  >
                    <span
                      className={`location-symbol pin-${location.category}`}
                    >
                      {categories[location.category].symbol}
                    </span>
                    <span>
                      <small>{categories[location.category].label}</small>
                      <strong>{location.name}</strong>
                      <span className="location-caption">
                        Auf der Karte ansehen
                      </span>
                    </span>
                    <span className="arrow">↗</span>
                  </button>
                ))
              )}
            </div>
            <div className="data-note">
              <span className="note-icon">ⓘ</span>
              <div>
                <strong>
                  {snapshot?.mode === "live"
                    ? "Verbundene Datenquelle"
                    : "Eine erste Orientierung"}
                </strong>
                <p>
                  {snapshot?.mode === "live"
                    ? "Die Standorte werden von der verbundenen Datenquelle bereitgestellt."
                    : "Beispielstandorte, keine Live-Messwerte. Die Positionen dienen der Orientierung."}
                </p>
                {snapshot?.updatedAt && (
                  <small>
                    Stand:{" "}
                    {new Date(snapshot.updatedAt).toLocaleString("de-CH")}
                  </small>
                )}
              </div>
            </div>
          </aside>
          <section className="map-panel" aria-label="Basel Karte">
            <BaselMap
              locations={visible}
              selectedId={selectedId}
              onSelect={setSelectedId}
              resetKey={resetKey}
            />
            <div className="map-heading">
              <span className="map-label">
                <i /> BASEL, SCHWEIZ
              </span>
              <button
                className="reset-button"
                onClick={() => {
                  setSelectedId(null);
                  setResetKey(resetKey + 1);
                }}
              >
                ⌖ <span>Basel zentrieren</span>
              </button>
            </div>
            {selected && (
              <div className="detail-card">
                <button
                  className="close-button"
                  aria-label="Standortdetails schliessen"
                  onClick={() => setSelectedId(null)}
                >
                  ×
                </button>
                <p className="eyebrow">{categories[selected.category].label}</p>
                <h3>{selected.name}</h3>
                <p>{selected.description}</p>
              </div>
            )}
            <div className="map-badge">
              {snapshot?.mode === "live"
                ? "Verbundene Standorte"
                : "Beispielstandorte"}
              <span>•</span> OpenStreetMap
            </div>
          </section>
        </div>
        <footer>
          <span>
            BioValley <span className="footer-dot">·</span> HackAmRhein 2026
          </span>
          <span>Eine Region. Viele Verbindungen.</span>
        </footer>
      </main>
    </div>
  );
}
