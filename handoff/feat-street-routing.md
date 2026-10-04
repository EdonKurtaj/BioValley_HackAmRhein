# Street routing for the frontend demo

Status: done; reviewed and verified with updated main

## Goal

Follow actual streets with MapLibre GL Directions and demonstrate a continuous traffic reroute.

## Done

- Captured full OSRM driving geometry and alternatives for four synthetic shipment endpoints in config/demo-road-routes.json; refresh through scripts/cache-demo-road-routes.py.
- Added candidate travel-time ranking, directed closure exclusion, shared-prefix compatibility and suitability checks in src/risk_assessment/road_routes.py and demo.py.
- Reroute scenario recommends an alternative then switches at five replay minutes, updating movement, ETA, slack and distance. Original path becomes dashed; missing alternatives keep the primary path.
- MapLibre Directions subclass renders cached server-planned routes; truck animation follows street corners. Optional routing metadata lives in frontend/src/interfaces.ts.
- Updated sources, design and run/demo instructions.
- Keep the original simulated closure marker and incident visible after rerouting, labelled avoided; show the original 45-minute delay in route status. Active-route counts/scoring exclude the avoided section.
- Made the rerouting truck explicit in the scenario selector (BV-104), with persistent route-status labels on its card, map and top of details; added Routenunterschied ansehen to focus the actual divergent streets.
- Reviewed frontend and routing: autoplay on initial load/scenario/restart, Play restarts completed replays, clock accounts for elapsed seconds, and restart resets the attention filter.
- Preserve marker progress on looping/repeated road geometry; scenario reset does not animate backwards. Incident selection no longer recentres the map on every poll or rebuilds unchanged popups.
- Correct remaining route time by subtracting the shared travelled prefix; hide unsuitable alternatives. A hold before rerouting prevents switching; a later hold freezes on the active alternative and keeps quality review prominent.
- Center truck symbols directly on their geographic road point, with each ID badge centered above the symbol so badge width no longer shifts the vehicle icon.
- Checked the built demo at a zoomed-out Basel view; the four truck symbols sit on their route lines while the labels stay legible. Frontend lint and build pass.
- Combined updated main bb37917 without conflicts, preserving the multiple-counter, one-minute traffic polling, bounded Supabase reads and valid Port observation fixes. The user explicitly requested this frontend/main integration.

## Verification

- Combined version: all 127 backend tests, 59 collector tests and 23 frontend tests pass; TypeScript, formatting, production build, documentation and privacy checks pass.
- Browser checked: street paths render, reroute switches at five replay minutes with updated ETA, restart restores the primary path, and no console errors were reported.
- Server restarted on port 8001; browser verification must leave the replay playing. Initial load, scenario selection and restart continue automatically.

## Next

- Complete the explicitly requested main integration and push; keep the feature branch for recovery.
- To connect observed incidents later, provide verified remaining-route edge matches and suitable truck paths; do not apply regional alerts automatically.

## Limits

OSRM driving paths do not establish truck suitability or live-traffic routing. Only returned candidates are searched; no guarantee of a global second-shortest path. Demo timing, GPS, traffic and telemetry stay simulated. Tiles require internet; route replay uses the local cache.

Later: split the large MapLibre production bundle if loading speed becomes a problem; the build currently warns about its size.

## Resume

Continue feat/street-routing. Read this file and docs/design.md. Verify Umleitung in the browser; run root unittest checks plus npm test/lint/build in frontend. Keep quality holds above route advice.
