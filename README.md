# BioValley · Basel regional overview

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

A Basel map frontend for exploring regional logistics, Rhine and weather context, with independently runnable data collection scripts and a Supabase schema.

## The problem

The prototype brings regional context into one place for a supply-risk dashboard. See [the initial frontend scope](docs/design.md).

## How to run it

Use Node.js 22.12+ or 24 LTS and npm. From the repository folder:

```sh
cd frontend
npm ci
npm run dev
```

Open the local URL printed by Vite. No backend or database credentials are needed for the default demo. Internet access is needed for OpenStreetMap tiles.

```sh
npm test
npm run lint
npm run build
npm run preview
```

`npm run format` formats the frontend. `npm test` checks TypeScript contracts and API boundary validation. The production output is generated in `frontend/dist/`.

## Connect a backend

The single shared map contract is [frontend/src/interfaces.ts](frontend/src/interfaces.ts); HTTP response validation and demo data live in [the adapter](frontend/src/data/mapData.ts). Serve `GET /map` under your API base URL using that JSON contract. Then create a local `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api
```

Restart Vite after changing it. The frontend requests `http://localhost:8000/api/map`. For a separate origin, the backend must allow the frontend origin through CORS. All `VITE_` values are public browser configuration: never use credentials here. For deployment, supply the API URL when building and use HTTPS or a same-origin `/api` reverse proxy. Keep backend responses compatible with the contract to avoid UI changes.

Backend failures remain visible with a retry action. The map itself stays available even if the location API is unavailable. The existing [Python requester and database setup](supabase/README.md) remain independent; connecting their results to the map endpoint is a future task.

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

The screen currently shows labelled example locations, not live readings or risk scores. Coordinates are illustrative. No operational or medical decisions should be inferred from them. See [scope and limits](docs/design.md).

## Team

@Elton53
