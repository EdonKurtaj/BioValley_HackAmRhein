# Local risk assessment backend

## State

Implemented on `feat/local-risk-assessment`; calculations run from saved requester snapshots and deterministic scenario inputs. Supabase remains disconnected.

## Done

- Added shared Python contracts, thermal measurement/simulation calculations, local snapshot summaries, robust traffic anomaly and Port Rhine high-water helpers, and explainable action selection.
- Used exact linear limit-crossing minutes and degree-hour areas; long sensor gaps are not interpolated, and unknown sensor accuracy triggers human review.
- Removed the unvalidated risk score from the Supabase draft schema and stopped anonymous client access to materials, lots, shipments, and decisions.
- Added run instructions and calculation tests; 12 tests pass, compileall passes, doc-check passes.

## Next

- Refresh the local observations before interpreting the weather context; the currently saved observation snapshot is stale.
- Add a qualified route baseline and obtain product/package-specific temperature handling inputs before treating this as operational evidence.
- Connect temperature sensor series and route ETA evidence through the shared contracts; then design authenticated tenant access before any customer data is stored/read in a client.
- Choose a Python environment manager (pixi preferred, optional) when the team wants a reproducible project environment; current backend uses only the standard library.
