import type { FeedMode, DemoScenario } from "../interfaces";
import { scenarioLabels } from "../config/dashboard";

export function ReplayControls({
  mode,
  activeCount,
  needsAttention,
  scenario,
  onScenario,
  playing,
  onPlay,
  onRestart,
  canPlay,
}: {
  mode: FeedMode;
  activeCount: number;
  needsAttention: number;
  scenario: DemoScenario;
  onScenario: (scenario: DemoScenario) => void;
  playing: boolean;
  onPlay: () => void;
  onRestart: () => void;
  canPlay: boolean;
}) {
  return (
    <div className="fleet-toolbar">
      <div>
        <h2>
          Transportübersicht <span>{activeCount}</span>
        </h2>
        <p>
          {mode === "demo"
            ? `${needsAttention} Transporte mit Handlungsbedarf · synthetische GPS-Positionen`
            : "Echte Transporte erscheinen nach Anbindung eines GPS- und Sensorfeeds."}
        </p>
      </div>
      {mode === "demo" && (
        <div className="replay-controls">
          <label>
            Szenario
            <select
              value={scenario}
              onChange={(event) =>
                onScenario(event.target.value as DemoScenario)
              }
            >
              {Object.entries(scenarioLabels).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button
            className="replay-button"
            disabled={!canPlay}
            onClick={onPlay}
          >
            {playing ? "Ⅱ Pause" : "▶ Abspielen"}
          </button>
          <button
            className="replay-button"
            onClick={onRestart}
            aria-label="Demo neu starten"
          >
            ↺ Neustart
          </button>
          <small>1 Sekunde = 1 Demo-Minute</small>
        </div>
      )}
    </div>
  );
}
