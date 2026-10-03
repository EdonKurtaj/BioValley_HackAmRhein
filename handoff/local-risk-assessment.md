# Local risk assessment backend

## State

Implemented on `feat/local-risk-assessment`; calculations run from saved requester snapshots and deterministic scenario inputs. Supabase remains disconnected. The current CLI demo follows Open Data → Disturbance Detection → Risk Assessment → Manufacturing Decision → a terminal Factory Dashboard summary.

## Done

- Added shared Python contracts, thermal measurement/simulation calculations, local snapshot summaries, robust traffic anomaly and Port Rhine high-water helpers, and explainable action selection.
- Used exact linear limit-crossing minutes and degree-hour areas; long sensor gaps are not interpolated, and unknown sensor accuracy triggers human review.
- Added a weighted 0–100 manufacturing-priority index with numeric thermal, route, and urgency components; missing inputs widen the output into a score interval instead of being treated as zero.
- Kept the priority score separate from product-quality review: a simulated box-temperature excursion can trigger review, but the score itself does not order quarantine or establish product damage.
- Added a five-case Normal/Buffer/Expedite/Reroute/combined demo and structured JSON output (`--scenario all --output-format json`) for later dashboard visualization.
- Current fetched weather and Rhine data are fresh; traffic observations are about 61 hours old and are marked stale, so the live-data score remains partial/uncertain.
- The previous no-score choice in `docs/decisions.md` is superseded by its newer score decision entry.
- The CLI now defaults to observed-data-only mode; package/route scenarios require `--scenario`. The current score excludes stale weather/traffic and Rhine without a supplied ship leg; last-observation weather context remains visible but is not treated as current.
- Scenario CLI output now defaults to a readable summary that prints `Current Risk Score: X/100`, evidence-group coverage and score-weight coverage separately; `--output-format json` preserves the structured score bounds and coverage for dashboard use.
- Scenario score weights are now thermal 50%, urgency 30%, route 20%; observed weights are weather context 40%, urgency 35%, Rhine 15%, traffic 10%. CLI output includes a separate `System Suggestion` derived from score thresholds and route/urgency triggers.
- Suggestion bands: ≥50 score or ≥70 urgency component => Expedite; ≥20 score or a route disturbance => Buffer; fewer than half the evidence groups available => Monitor; otherwise Normal. Feasible alternate on a matching restriction => Reroute. A package quality-review condition is combined with the operational recommendation (for example, `Quality review + Expedite`).
- Coverage now counts usable input groups (four in observed mode, three in scenario mode); score-weight coverage is reported separately. The observed CLI's `Data review` lists considered versus omitted/context-only inputs with reasons, and JSON includes `data_review` and `evidence_coverage`.

## Next

- The current saved weather and Rhine readings are fresh; weather remains regional context only. Traffic observations remain delayed and do not support a live disturbance determination.
- Refresh the local snapshots before running observed-data mode; current saved weather, traffic and Port snapshots have aged beyond the current freshness window. At the last observed weather values (18.4 °C, no rain, 7.2 km/h gust), the context severity is zero, not a simulated package excursion.
- Add a qualified route baseline and obtain product/package-specific temperature handling inputs before treating this as operational evidence; calibrate the prototype weights and component scales with the team and shipment outcomes.
- Connect temperature sensor series and route ETA evidence through the shared contracts; then design authenticated tenant access before any customer data is stored/read in a client.
- The terminal dashboard is a logic demo, not yet a web factory dashboard; build/wire the UI after the team chooses its presentation approach.
- Choose a Python environment manager (pixi preferred, optional) when the team wants a reproducible project environment; current backend uses only the standard library.
