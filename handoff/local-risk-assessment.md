# Local risk assessment backend

## State

Implemented on `feat/local-risk-assessment`; calculations run from saved requester snapshots and deterministic scenario inputs. Supabase remains disconnected. The current CLI demo follows Open Data → Disturbance Detection → Risk Assessment → Manufacturing Decision → a terminal Factory Dashboard summary.

## Done

- Added shared Python contracts, thermal measurement/simulation calculations, local snapshot summaries, robust traffic anomaly and Port Rhine high-water helpers, and explainable action selection.
- Used exact linear limit-crossing minutes and degree-hour areas; long sensor gaps are not interpolated, and unknown sensor accuracy triggers human review.
- Removed the unvalidated risk score from the Supabase draft schema and stopped anonymous client access to materials, lots, shipments, and decisions.
- Added run instructions and calculation tests; 13 tests pass, compileall passes, doc-check passes.
- Added local traffic disturbance detection with freshness and like-for-like baseline checks, plus a four-case Normal/Buffer/Expedite/Reroute demo. Current fetched weather and Rhine data are fresh; traffic observations are about 61 hours old and are marked stale.

## Next

- The current saved weather and Rhine readings are fresh; weather remains regional context only. Traffic observations remain delayed and do not support a live disturbance determination.
- Add a qualified route baseline and obtain product/package-specific temperature handling inputs before treating this as operational evidence.
- Connect temperature sensor series and route ETA evidence through the shared contracts; then design authenticated tenant access before any customer data is stored/read in a client.
- The terminal dashboard is a logic demo, not yet a web factory dashboard; build/wire the UI after the team chooses its presentation approach.
- Choose a Python environment manager (pixi preferred, optional) when the team wants a reproducible project environment; current backend uses only the standard library.
