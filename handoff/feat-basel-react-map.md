# React Basel map

Status: verification in progress

## Goal

Build an independently runnable React frontend with a Basel map and a stable backend boundary.

## Done

- Separate frontend with React, TypeScript, Vite and MapLibre GL JS; production build passes.
- Demo locations, category filtering, selection and recentering.
- HTTP adapter with response validation, loading, errors and retry.
- Shared contract and backend integration instructions.

## Next

- Run formatting and contract checks.
- Check browser rendering and interactions.
- Run privacy and documentation checks; save changes.

## Limits

No backend endpoint implemented. Existing Python and Supabase code is unchanged. Map images require internet; example locations are not exact sensor coordinates.

## Resume

Continue the React Basel map task from this handoff. Use frontend/src/interfaces.ts for the backend contract and README.md for run instructions.
