# Basel logistics dashboard

Administrative logistics staff need to see environmental disturbances and refrigerated shipments approaching a production deadline. The dashboard combines a Basel MapLibre map, regional measurement cards, an incident panel, a shipment list and selectable shipment details.

## Demo flow

Start in clearly labelled Demo mode. Select a truck to see its route, moving simulated position, departure, ETA, destination, package temperature/history, distance and production need-by time. Inspect the full weighted score and its explanation. Replay normal operation, traffic delay, an urgent shipment, a suitable alternative route or a temperature excursion. Pause, resume or restart the accelerated replay. Quality review takes precedence over transport advice; a synthetic hold freezes the affected truck's movement while temperature monitoring continues and its original ETA is labelled planning-only.

Switch to Live mode to retrieve saved environmental observations from Supabase through the backend. Show measurement timestamps and stale/missing inputs. Regional traffic messages are candidates for route review. No live shipment feed exists yet, so Live mode has an explicit empty shipment state. A failed live request remains an error and never substitutes demo evidence.

## Architecture

`frontend/` is an independent Vite React application. The existing Python collection code and Supabase schema remain separately runnable. UI components consume the validated dashboard response; they never access the database or ingestion files directly. The shared contract lives in [interfaces.ts](../frontend/src/interfaces.ts).

The local Python HTTP server reuses the existing thermal exposure, priority and decision functions and implements GET /api/dashboard. It starts the existing collector for periodic source refresh while it runs. Demo replay inputs live in config/demo-transports.json. Map interpolation only animates provided route geometry; it does not calculate risk. The server also serves the built frontend. Vite proxies /api to the server in development. Database credentials stay on the server.

## Out of scope

Real GPS, package sensors, validated product stability rules, automatic dispatch, authentication and qualified routing are outside this demo. Route geometry, transport identities, delays, temperatures and timing in Demo mode are synthetic. Route distances follow those illustrative polylines and are not verified navigation distances. OpenStreetMap tiles require internet access. Demo evidence coverage describes completeness of synthetic inputs, not scientific validation.
