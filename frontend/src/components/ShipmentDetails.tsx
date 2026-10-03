import type { Shipment } from "../interfaces";
import {
  actionDescriptions,
  actionLabels,
  priorityLabels,
} from "../config/dashboard";

export function timeLabel(value: string | null, withDate = false) {
  if (!value) return "—";
  const date = new Date(value);
  const options = {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Zurich",
  } as const;
  return withDate
    ? date.toLocaleString("de-CH", {
        ...options,
        day: "2-digit",
        month: "2-digit",
      })
    : date.toLocaleTimeString("de-CH", options);
}

function TemperatureChart({ shipment }: { shipment: Shipment }) {
  const { minimumC, maximumC } = shipment.temperatureBand;
  const history = shipment.temperatureHistory;
  const low = Math.min(minimumC - 1, ...history.map((point) => point.value));
  const high = Math.max(maximumC + 1, ...history.map((point) => point.value));
  const y = (value: number) => 80 - ((value - low) / (high - low)) * 68;
  const start = Date.parse(history[0].at);
  const duration = Date.parse(history[history.length - 1].at) - start;
  const points = history
    .map(
      (point) =>
        `${28 + ((Date.parse(point.at) - start) / duration) * 232},${y(point.value)}`,
    )
    .join(" ");
  return (
    <div className="temperature-chart">
      <svg
        viewBox="0 0 285 112"
        role="img"
        aria-label={`Simulierte Pakettemperatur, Zielband ${minimumC} bis ${maximumC} Grad Celsius`}
      >
        <rect
          className="temperature-band"
          x="28"
          width="232"
          y={y(maximumC)}
          height={y(minimumC) - y(maximumC)}
        />
        {[minimumC, maximumC].map((value) => (
          <g key={value}>
            <line
              className="chart-guide"
              x1="28"
              x2="260"
              y1={y(value)}
              y2={y(value)}
            />
            <text x="4" y={y(value) + 3}>
              {value}°
            </text>
          </g>
        ))}
        <polyline
          className={`temperature-line ${shipment.thermal.quality_review_required ? "excursion" : ""}`}
          points={points}
        />
        <text x="28" y="105">
          {timeLabel(history[0].at)}
        </text>
        <text x="260" y="105" textAnchor="end">
          {timeLabel(history[history.length - 1].at)}
        </text>
      </svg>
      <small>
        Simulierter Verlauf · grün: {minimumC}–{maximumC} °C · keine reale
        Sensormessung
      </small>
    </div>
  );
}

export function ShipmentDetails({
  shipment,
}: {
  shipment: Shipment | undefined;
}) {
  if (!shipment)
    return (
      <aside className="shipment-details empty-detail">
        <span className="empty-icon">⌖</span>
        <h2>Transportdetails</h2>
        <p>Wähle einen Transport aus der Liste oder auf der Karte.</p>
        <p>Im Live-Modus ist noch kein GPS- oder Paketsensor-Feed verbunden.</p>
      </aside>
    );
  const score = shipment.score;
  const riskLabel =
    score.minimum === score.maximum
      ? score.minimum.toFixed(1)
      : `${score.minimum.toFixed(1)}–${score.maximum.toFixed(1)}`;
  return (
    <aside className="shipment-details" aria-label="Transportdetails">
      <div className="details-heading">
        <p className="eyebrow">TRANSPORTDETAILS · DEMO</p>
        <h2>{shipment.id}</h2>
        <p>{shipment.material}</p>
        <span className={`priority priority-${shipment.priority}`}>
          Priorität {priorityLabels[shipment.priority]}
        </span>
      </div>
      <div className={`recommendation action-${shipment.action}`}>
        <span className="eyebrow">EMPFEHLUNG</span>
        <strong>{actionLabels[shipment.action]}</strong>
        <p>{actionDescriptions[shipment.action]}</p>
        <details>
          <summary>Backend-Begründung</summary>
          <p lang="en">{shipment.reason}</p>
        </details>
      </div>
      <div className="shipment-metrics">
        <div>
          <small>Pakettemperatur</small>
          <strong>
            {shipment.temperatureC.toFixed(1)} <span>°C</span>
          </strong>
          <small>
            Ziel: {shipment.temperatureBand.minimumC}–
            {shipment.temperatureBand.maximumC} °C
          </small>
        </div>
        <div>
          <small>Prioritätsindex</small>
          <strong>
            {riskLabel}
            <span> / 100</span>
          </strong>
          <small>{score.coverage_percent.toFixed(0)} % Demo-Evidenz</small>
        </div>
      </div>
      <TemperatureChart shipment={shipment} />
      {shipment.thermal.quality_review_required && (
        <p className="hold-note">
          Qualitätshold: kontrolliert lagern und prüfen. Kein Weitertransport
          oder Produktionseinsatz ohne Freigabe.
        </p>
      )}
      {shipment.routing && (
        <p className="hold-note" role="status">
          {shipment.routing.message} · {shipment.routing.candidateCount}{" "}
          Routenkandidat(en).
          {shipment.routing.rerouted && " Gestrichelt: ursprüngliche Route."}
        </p>
      )}
      <dl className="shipment-facts">
        <div>
          <dt>Start</dt>
          <dd>{shipment.origin}</dd>
        </div>
        <div>
          <dt>Ziel</dt>
          <dd>{shipment.destination}</dd>
        </div>
        <div>
          <dt>Abfahrt</dt>
          <dd>{timeLabel(shipment.departureAt, true)}</dd>
        </div>
        <div>
          <dt>
            {shipment.status === "held"
              ? "Plan-ETA · Hold aktiv"
              : "Ankunft / Lieferdatum"}
          </dt>
          <dd>{timeLabel(shipment.etaAt, true)}</dd>
        </div>
        <div>
          <dt>Benötigt bis</dt>
          <dd>{timeLabel(shipment.neededAt, true)}</dd>
        </div>
        <div>
          <dt>Zeit vor Bedarf</dt>
          <dd>
            {shipment.slackMinutes} min · Puffer {shipment.bufferHours} h
          </dd>
        </div>
        <div>
          <dt>Verzögerung</dt>
          <dd>{shipment.delayMinutes} min simuliert</dd>
        </div>
        <div>
          <dt>Rest / Gesamtroute</dt>
          <dd>
            {shipment.remainingKm} / {shipment.distanceKm} km*
          </dd>
        </div>
        {shipment.alternateEtaAt && (
          <div>
            <dt>Umleitungs-ETA</dt>
            <dd>
              {timeLabel(shipment.alternateEtaAt, true)} · simulierte Fahrzeit
            </dd>
          </div>
        )}
      </dl>
      <div className="score-breakdown">
        <p className="eyebrow">SO ENTSTEHT DER INDEX</p>
        {(
          [
            ["thermal", "Thermische Belastung"],
            ["urgency", "Produktionsdringlichkeit"],
            ["route", "Routenstörung"],
          ] as const
        ).map(([key, label]) => (
          <div key={key}>
            <span>{label}</span>
            <strong>
              {score.weighted_points[key]?.toFixed(1) ?? "?"} Punkte
            </strong>
            <progress
              max={100}
              value={score.components[key] ?? 0}
              aria-label={`${label}: ${score.components[key] ?? "unbekannt"} von 100`}
            />
          </div>
        ))}
        <p>
          {score.evidence_coverage_available}/{score.evidence_coverage_total}{" "}
          Eingangsgruppen · {score.score_weight_coverage_percent.toFixed(0)} %
          Gewichtabdeckung. Vollständige synthetische Evidenz bedeutet keine
          wissenschaftliche Kalibrierung.
        </p>
      </div>
      <p className="detail-limit">
        *Straßengeometrie aus OSRM / OpenStreetMap. GPS, Temperaturen und Zeiten
        sind simuliert. Der Index erklärt Priorität; er gibt Material nicht
        frei.
      </p>
    </aside>
  );
}
