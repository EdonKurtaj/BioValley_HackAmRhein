# Basel map foundation

The first requested screen is a standalone React map of Basel. It provides geographic context for the existing weather, traffic and Rhine collection work. The first version lets users pan and zoom, filter illustrative locations, select a location and return to the Basel overview.

## Architecture

`frontend/` is an independent Vite React application. The existing Python collection code and Supabase schema remain separately runnable. UI components consume the map data adapter; they never access the database or ingestion files directly. The shared contract lives in [interfaces.ts](../frontend/src/interfaces.ts).

Default mode uses clearly labelled illustrative locations. Setting a public API base URL switches the adapter to HTTP. The backend can be written in any language as long as it serves the agreed contract. Database credentials stay on the server. Backend failures are shown as errors, never silently replaced by demo data.

## Out of scope

Live observations, risk calculations, shipment routes, authentication and backend endpoints are not part of this first screen. Example coordinates are for orientation, not exact sensor positions. Map tiles require internet access. No operational or quality decisions are made by this frontend.
