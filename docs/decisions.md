# Decisions

One line per decision, newest at the bottom. Never edit an old line; add a new one that says what it replaces.

Format: `- <date> · <decision> · @<github-username> · Affects: <tasks or areas> · Why: <short> · Instead of: <alternative, why not>`

- 2026-10-03 · Use an independent React/TypeScript/Vite frontend with npm, Leaflet and a map data adapter; define the HTTP contract in frontend/src/interfaces.ts · @Elton53 · Affects: frontend and future map API · Why: backend implementation can evolve without changing map components · Instead of: direct database access from UI, which couples the screen to storage.

