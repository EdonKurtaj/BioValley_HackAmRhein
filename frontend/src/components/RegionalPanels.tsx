import type {
  EnvironmentalSignal,
  RegionalAlert,
  FeedMode,
} from "../interfaces";
import { freshnessLabels } from "../config/dashboard";
import { timeLabel } from "./ShipmentDetails";

export function RegionalSignals({
  signals,
  loading,
}: {
  signals: EnvironmentalSignal[] | undefined;
  loading: boolean;
}) {
  return (
    <section className="signal-grid" aria-label="Relevante regionale Messdaten">
      {signals?.map((signal) => (
        <article
          key={signal.id}
          className={`signal-card severity-${signal.severity}`}
        >
          <div>
            <span>{signal.title}</span>
            <small className={`freshness freshness-${signal.freshness}`}>
              {freshnessLabels[signal.freshness]}
            </small>
          </div>
          <strong>
            {signal.value === null
              ? "—"
              : signal.value.toLocaleString("de-CH", {
                  maximumFractionDigits: 1,
                })}
            <span> {signal.unit}</span>
          </strong>
          <p>{signal.detail}</p>
          <small>
            {signal.source} · {timeLabel(signal.observedAt, true)}
          </small>
        </article>
      )) ??
        ["Lufttemperatur", "Verkehrsmeldungen", "Windböen", "Rheinpegel"].map(
          (title) => (
            <article className="signal-card loading-card" key={title}>
              <span>{title}</span>
              <strong>—</strong>
              <p>
                {loading
                  ? "Messdaten werden geladen …"
                  : "Keine Messdaten verfügbar"}
              </p>
            </article>
          ),
        )}
    </section>
  );
}

export function RegionalAlerts({
  alerts,
  mode,
  loading,
  hasData,
}: {
  alerts: RegionalAlert[] | undefined;
  mode: FeedMode;
  loading: boolean;
  hasData: boolean;
}) {
  return (
    <section className="regional-alerts">
      <div>
        <p className="eyebrow">WETTER & VERKEHR</p>
        <h2>Relevante Meldungen</h2>
        <p>
          {mode === "demo"
            ? "Explizite Demo-Störungen für die dargestellten Fahrten."
            : "Regionale Kandidaten · vor einer Maßnahme den Routenbezug prüfen."}
        </p>
      </div>
      <div className="alert-list">
        {alerts?.length ? (
          alerts.map((alert) => (
            <article key={alert.id}>
              <span className={`alert-icon ${alert.kind}`}>
                {alert.kind === "traffic" ? "!" : "☀"}
              </span>
              <div>
                <strong>{alert.title}</strong>
                <p>{alert.detail}</p>
                <small>
                  {freshnessLabels[alert.freshness]} ·{" "}
                  {timeLabel(alert.observedAt, true)} ·{" "}
                  {mode === "demo" ? "Simuliert" : "Supabase"}
                </small>
              </div>
            </article>
          ))
        ) : (
          <p className="state-message">
            {loading
              ? "Meldungen werden geladen …"
              : hasData
                ? "Keine Meldungen in diesem Datenstand. Das beweist keine freie Transportroute."
                : "Keine Daten verfügbar."}
          </p>
        )}
      </div>
    </section>
  );
}
