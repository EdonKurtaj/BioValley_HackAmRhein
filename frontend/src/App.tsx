import { RegionalSignals, RegionalAlerts } from "./components/RegionalPanels";
import { TransportSidebar } from "./components/TransportSidebar";
import { ReplayControls } from "./components/ReplayControls";
import { useEffect, useRef, useState } from "react";
import { BaselMap } from "./components/BaselMap";
import { ShipmentDetails, timeLabel } from "./components/ShipmentDetails";
import { loadDashboard } from "./data/dashboardData";
import {
  DASHBOARD_POLL_MS,
  LIVE_POLL_MS,
  API_TIMEOUT_MS,
} from "./config/dashboard";
import type { DashboardSnapshot, DemoScenario, FeedMode } from "./interfaces";

export default function App() {
  const [mode, setMode] = useState<FeedMode>("demo");
  const [scenario, setScenario] = useState<DemoScenario>("fleet");
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [anchor, setAnchor] = useState(() => new Date().toISOString());
  const elapsed = useRef(0);
  const [selectedId, setSelectedId] = useState<string | null>("BV-104");
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(
    null,
  );
  const [resetKey, setResetKey] = useState(0);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let active = true;
    let timer: number;
    let controller: AbortController;
    setLoading(true);
    setSnapshot(null);
    setError("");
    async function refresh() {
      controller = new AbortController();
      const timeout = window.setTimeout(
        () => controller.abort(),
        API_TIMEOUT_MS,
      );
      try {
        const data = await loadDashboard(
          mode,
          scenario,
          elapsed.current,
          anchor,
          controller.signal,
        );
        if (active) {
          setSnapshot(data);
          setError("");
        }
      } catch (reason) {
        if (active)
          setError(
            reason instanceof Error && reason.name !== "AbortError"
              ? reason.message
              : "Die Datenquelle antwortet nicht. Bitte erneut versuchen.",
          );
      } finally {
        window.clearTimeout(timeout);
        if (active) {
          setLoading(false);
          timer = window.setTimeout(
            refresh,
            mode === "demo" ? DASHBOARD_POLL_MS : LIVE_POLL_MS,
          );
        }
      }
    }
    void refresh();
    return () => {
      active = false;
      window.clearTimeout(timer);
      controller?.abort();
    };
  }, [mode, scenario, anchor, attempt]);

  useEffect(() => {
    if (!playing || mode !== "demo" || !snapshot || error) return;
    const timer = window.setInterval(() => {
      elapsed.current = Math.min(
        snapshot.simulation?.maximumMinutes ?? 180,
        elapsed.current + (snapshot.simulation?.minutesPerSecond ?? 1),
      );
      if (elapsed.current >= (snapshot.simulation?.maximumMinutes ?? 180))
        setPlaying(false);
    }, DASHBOARD_POLL_MS);
    return () => window.clearInterval(timer);
    // Replay timing uses a ref so requests are serial rather than aborted every second.
  }, [playing, mode, !!snapshot, error]);

  function restart(nextScenario = scenario) {
    setPlaying(false);
    elapsed.current = 0;
    setAnchor(new Date().toISOString());
    setScenario(nextScenario);
    setSelectedId("BV-104");
    setSelectedLocationId(null);
  }

  function switchMode(next: FeedMode) {
    if (next === mode) return;
    setPlaying(false);
    setSnapshot(null);
    setSelectedLocationId(null);
    setMode(next);
  }

  const shipments = snapshot?.shipments ?? [];
  const selected = shipments.find((shipment) => shipment.id === selectedId);
  const locations = snapshot?.locations ?? [];
  const selectedLocation = locations.find(
    (location) => location.id === selectedLocationId,
  );
  const activeShipments = shipments.filter(
    (shipment) => shipment.status !== "delivered",
  );
  const needsAttention = activeShipments.filter(
    (shipment) => shipment.action !== "normal",
  ).length;

  return (
    <div className="app-shell">
      <header className="header">
        <a className="brand" href="/" aria-label="BioValley Startseite">
          <span className="brand-icon">
            b<span>v</span>
          </span>
          <span>
            BioValley<small>LOGISTICS INTELLIGENCE</small>
          </span>
        </a>
        <span className="header-section">
          Region Basel <span className="slash">/</span> Transportleitstand
        </span>
        <span className="prototype">
          <i />
          Prototyp
        </span>
      </header>
      <main className="dashboard-main">
        <div className="page-heading">
          <div>
            <p className="eyebrow">KÜHLKETTE & LOGISTIK</p>
            <h1>Lieferungen im Blick.</h1>
            <p className="subtitle">
              Messwerte einordnen. Engpässe erkennen. Die nächste Maßnahme
              verstehen.
            </p>
          </div>
          <div className="feed-control">
            <div className="feed-switch" aria-label="Datenmodus">
              {(["demo", "live"] as const).map((feed) => (
                <button
                  key={feed}
                  aria-pressed={mode === feed}
                  className={mode === feed ? "active" : ""}
                  onClick={() => switchMode(feed)}
                >
                  {feed === "demo" ? "◈ Demo-Feed" : "● Live-Feed"}
                </button>
              ))}
            </div>
            <small>
              {mode === "demo"
                ? "Alle Transport- und Messdaten sind simuliert"
                : "Messungen aus Supabase · Zeitstempel beachten"}
            </small>
          </div>
        </div>
        <div className={`provenance-banner ${mode}`} role="status">
          <span>
            <strong>{mode === "demo" ? "DEMO" : "LIVE"}</strong>{" "}
            {snapshot?.sourceLabel ??
              (mode === "demo"
                ? "Synthetische Flotte wird geladen"
                : "Supabase-Beobachtungen werden geladen")}
          </span>
          <span>
            {snapshot?.updatedAt
              ? `${mode === "demo" ? "Simulationszeit" : "Abruf"}: ${timeLabel(snapshot.updatedAt, true)}`
              : "Verbindung wird hergestellt …"}
          </span>
        </div>
        {error && (
          <div className="connection-error" role="alert">
            <span>
              {error}
              {snapshot
                ? " Angezeigte Daten stammen aus dem letzten erfolgreichen Abruf."
                : ""}
            </span>
            <button
              className="text-button"
              onClick={() => setAttempt(attempt + 1)}
            >
              Erneut versuchen ↗
            </button>
          </div>
        )}
        <RegionalSignals signals={snapshot?.signals} loading={loading} />
        <ReplayControls
          mode={mode}
          activeCount={activeShipments.length}
          needsAttention={needsAttention}
          scenario={scenario}
          onScenario={restart}
          playing={playing}
          onPlay={() => setPlaying(!playing)}
          onRestart={() => restart()}
          canPlay={!!snapshot && !error}
        />
        <div className="operations-layout">
          <TransportSidebar
            shipments={shipments}
            selectedId={selectedId}
            onSelect={setSelectedId}
            filter={filter}
            onFilter={setFilter}
            mode={mode}
            loading={loading}
            transportSource={snapshot?.transportSource}
          />
          <section className="map-panel" aria-label="Basel Transportkarte">
            <BaselMap
              locations={locations}
              selectedId={selectedLocationId}
              onSelect={setSelectedLocationId}
              resetKey={resetKey}
              shipments={shipments}
              selectedShipmentId={selectedId}
              onSelectShipment={setSelectedId}
            />
            <div className="map-heading">
              <span className="map-label">
                <i /> BASEL & ANFAHRTSROUTEN
              </span>
              <button
                className="reset-button"
                onClick={() => {
                  setResetKey(resetKey + 1);
                  setSelectedLocationId(null);
                }}
              >
                ⌖ Übersicht
              </button>
            </div>
            {selectedLocation && (
              <div className="detail-card">
                <button
                  className="close-button"
                  aria-label="Standortdetails schließen"
                  onClick={() => setSelectedLocationId(null)}
                >
                  ×
                </button>
                <p className="eyebrow">REGIONALER KONTEXT</p>
                <h3>{selectedLocation.name}</h3>
                <p>{selectedLocation.description}</p>
              </div>
            )}
            <div className="map-badge">
              {mode === "demo"
                ? "Demo-LKW · illustrative Routen"
                : "Regionale Beobachtungen · kein GPS"}
              <span>•</span>OpenStreetMap
            </div>
          </section>
          <ShipmentDetails shipment={selected} />
        </div>
        <RegionalAlerts
          alerts={snapshot?.alerts}
          mode={mode}
          loading={loading}
          hasData={!!snapshot}
        />
        <footer>
          <span>BioValley · HackAmRhein 2026</span>
          <span>
            Planungsempfehlungen · keine automatische Disposition oder
            Produktfreigabe
          </span>
        </footer>
      </main>
    </div>
  );
}
