# Street routing for the frontend demo

Status: done; verified locally, ready for review

## Goal

Follow actual streets with MapLibre GL Directions and demonstrate a continuous traffic reroute.

## Done

- Captured full OSRM driving geometry and alternatives for four synthetic shipment endpoints in config/demo-road-routes.json; refresh through scripts/cache-demo-road-routes.py.
- Added candidate travel-time ranking, directed closure exclusion, shared-prefix compatibility and suitability checks in src/risk_assessment/road_routes.py and demo.py.
- Reroute scenario recommends an alternative then switches at five replay minutes, updating movement, ETA, slack and distance. Original path becomes dashed; missing alternatives keep the primary path.
- MapLibre Directions subclass renders cached server-planned routes; truck animation follows street corners. Optional routing metadata lives in frontend/src/interfaces.ts.
- Updated sources, design and run/demo instructions.
- Made the rerouting truck explicit in the scenario selector (BV-104), with persistent route-status labels on its card, map and top of details; added Routenunterschied ansehen to focus the actual divergent streets.

## Verification

- All 108 backend tests and 20 frontend tests pass; TypeScript, formatting, production build and documentation checks pass.
- Browser checked: street paths render, reroute switches at five replay minutes with updated ETA, restart restores the primary path, and no console errors were reported.

## Next

- Review the feature branch and merge only after explicit approval.
- To connect observed incidents later, provide verified remaining-route edge matches and suitable truck paths; do not apply regional alerts automatically.

## Limits

OSRM driving paths do not establish truck suitability or live-traffic routing. Only returned candidates are searched; no guarantee of a global second-shortest path. Demo timing, GPS, traffic and telemetry stay simulated. Tiles require internet; route replay uses the local cache.

## Resume

Continue feat/street-routing. Read this file and docs/design.md. Verify Umleitung in the browser; run root unittest checks plus npm test/lint/build in frontend. Keep quality holds above route advice.
