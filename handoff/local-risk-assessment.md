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
- Suggestion bands: ≥50 score or ≥70 urgency component => Expedite; ≥20 score or a route disturbance => Buffer; fewer than half the evidence groups available => Monitor; otherwise Normal. Feasible alternate on a matching restriction => Reroute. A package quality-review condition now overrides every operational recommendation. Both decision outputs require controlled storage and block onward delivery/production use until authorized release.
- Coverage now counts usable input groups (four in observed mode, three in scenario mode); score-weight coverage is reported separately. The observed CLI's `Data review` lists considered versus omitted/context-only inputs with reasons, and JSON includes `data_review` and `evidence_coverage`.

## Next

- The current saved weather and Rhine readings are fresh; weather remains regional context only. Traffic observations remain delayed and do not support a live disturbance determination.
- Refresh the local snapshots before running observed-data mode; current saved weather, traffic and Port snapshots have aged beyond the current freshness window. At the last observed weather values (18.4 °C, no rain, 7.2 km/h gust), the context severity is zero, not a simulated package excursion.
- Add a qualified route baseline and obtain product/package-specific temperature handling inputs before treating this as operational evidence; calibrate the prototype weights and component scales with the team and shipment outcomes.
- Connect temperature sensor series and route ETA evidence through the shared contracts; then design authenticated tenant access before any customer data is stored/read in a client.
- The terminal dashboard is a logic demo, not yet a web factory dashboard; build/wire the UI after the team chooses its presentation approach.
- Choose a Python environment manager (pixi preferred, optional) when the team wants a reproducible project environment; current backend uses only the standard library.

## Quality-hold correction — done

- Shared hold wording and early return prevent score, deadline, or alternate-route triggers from producing combined delivery recommendations.
- Regression tests cover measured 10 °C exposure with ample slack, missing/uncertain/incomplete evidence, deadline/restriction overrides, and unaffected logistics paths.
- Remaining review findings are outside this correction; the four existing score-weight test failures remain to be addressed separately.

## Temperature-history correction — done

- Added keyword-only `evaluated_at` (defaults to current UTC) and `monitoring_started_at` to the thermal analyzer. Missing start, fewer than two readings, missing beginning, stale last reading, and internal gaps require quality review and omit the thermal score.
- The existing configurable `max_gap` (15-minute demo default) also bounds endpoint age; no unmeasured exposure is extrapolated. Invalid time boundaries and readings outside the interval are rejected.
- Scenario CLI passes the explicit simulated interval and exposes `incomplete_history`; historical tests now use explicit evaluation times.
- Nine new regression tests and the three quality-hold tests pass. The four previously known score-weight failures remain outside this correction.

## Port measurement-freshness correction — done

- Rhine eligibility now uses the selected Basel-Rheinhalle measurement timestamp, with a named 30-minute demo freshness limit. Fetch age remains informational only.
- Parse page timestamps in Europe/Zurich and aware ISO timestamps into UTC; missing, invalid, future and DST-ambiguous/nonexistent times are unknown and excluded.
- JSON reports observation age, UTC timestamp and freshness reason; terminal shows measurement and page-fetch age separately.
- Seven regression tests pass, including a freshly fetched 2020 reading that cannot trigger rerouting and fresh readings that still can. The four pre-existing score-weight test failures remain open.

## Temperature-boundary correction — done

- Evaluate the non-positive case before the non-negative case in `_positive_duration`; two zero deviations now contribute zero excursion minutes.
- Five new regression tests cover constant 2/8 °C, boundary-to-in-band transitions, boundary-to-outside transitions in both directions, actual crossings, and preserved sensor-uncertainty review.
- The four known score-weight test failures remain outside this correction.

## Shipment decision correction — done

- Scenario and observed outputs share decide_action; suggestions render the same action/reason. Scores remain informational. Holds from point 1 still override all actions.
- Added optional counter mappings, handling context and alternative suitability/ETA to RouteEvidence; monitor is an additive action. All CLI callers and relevant tests updated.
- Weather is scored only for confirmed exposed handling; traffic detection filters exact site/direction/lane mappings before selecting the newest observation and baseline. No mapping means unknown.
- Alternative must be suitable for the material, earlier than the original ETA and on time; restricted routes without verified alternatives produce Monitor. Buffer/Expedite require ETA/need-by; Normal requires package, route and handling evidence.
- Added CLI flags for these inputs and labeled alternate suitability as operator/scenario evidence. Updated README and risk docs; schema.sql unchanged.
- Nine new shipment-policy tests pass. All 54 tests run: 50 pass, with the same four pre-existing score-weight failures remaining for point 6.

## Score-weight test correction — done

- Preserved the documented 50% thermal / 30% urgency / 20% route policy. Moved scenario weights and reference scales into config.py; the CLI summary now reads the configured values.
- Corrected stale 40/35/25 test expectations: full contributions 50/30/20, thermal-only half severity bounds 25–75, half route severity contributes 10 with bounds 10–90.
- Corrected the previously masked coverage assertion: output rounds 1/3 evidence coverage to 33.3%, while group counts remain 1/3.
- Added independent policy-total and mixed-severity checks. All 56 risk-engine tests pass; point 7 (collector/main/schema integration) remains separate.

## Collector integration (review point 7)

- Combined with origin/main collector; see [integration handoff](collector-risk-integration.md).
- Original schema retained; access restrictions are a separate, unapplied migration.
