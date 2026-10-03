# Logistics dashboard

Status: done

## Goal
Replace the map-only screen with an operator dashboard, shipment details, animated demo truck routes, server-side assessment and a visible Live/Demo switch.

## State
Implemented on `feat/logistics-dashboard` from the shared main baseline. Existing Python thermal, priority and decision policies are reused server-side.

## Done
- Implemented the Python dashboard API, deterministic fleet replay and shared dashboard/shipment contracts.
- Connected the React operator dashboard, list, details, temperature chart, animated MapLibre routes and Live/Demo controls.
- Backend scenarios produce Normal, Buffer, Expedite, Reroute and quality review with full synthetic evidence coverage.
- Browser verification found and fixed MapLibre 6 ESM worker bundling; route lines now render.
- Real Supabase read succeeded for all five sources. The MSYS interpreter needs a trusted CA bundle; the Windows launcher finds the existing Git CA file without disabling certificate verification.
- Verified 98 Python and 18 frontend tests, TypeScript/format checks and production build. Browser verified movement, quality hold, alternative-route recommendation and Live/Demo switching. Current traffic appears first; unresolved validity is labelled unknown and is not plotted as an active incident.

## Next
1. Review the branch before merging; merge requires explicit approval.
2. Connect a real shipment feed and qualified road-routing provider as separate work. Supabase weather and gauge observations can be stale; the UI exposes their timestamps.

## Decisions and limits
Demo supplies package readings, explicit route disturbances, ETAs and need-by times, so its score can have complete synthetic evidence. Live environmental data alone cannot establish package or route status. Routes are authored illustrative corridors, not turn-by-turn navigation. A synthetic temperature hold stops the affected demo truck while temperature monitoring continues; its nominal ETA is labelled planning-only. No real recommendation executes dispatch or releases goods.

## Resume
Continue the logistics dashboard on feat/logistics-dashboard. Read this handoff, frontend/src/interfaces.ts and docs/design.md; finish the Next steps and retain honest Live/Demo provenance.
