# Basel cold-chain risk prototype

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

This prototype explores how weather, traffic, and Rhine signals can inform cold-chain logistics planning for a generic refrigerated material. Package-temperature scenarios and observed local conditions are separate evidence.

## The problem

A Basel-area factory needs a critical refrigerated material on time while preserving its 2–8 °C handling conditions. This demo combines public environmental measurements with explicit shipment context to explain planning recommendations.

## How to run it

From the repository root, run the latest saved open-data observations only. The CLI reads weather, traffic, Rhine, Port and road evidence from Supabase. Credentials are read server-side from the local .env; failed database reads do not fall back to local archives. This does not simulate package temperature, traffic, or ETA:

```sh
PYTHONPATH=src python3 -m risk_assessment.cli
```

The collector keeps local archives and stores measurements in Supabase when the local `.env` is configured. The assessment selects the newest MeteoSwiss station batch from `observations` and checks freshness from its source `observed_at` timestamp. Decision persistence is not implemented. See [collector setup](pythontest/README.md) and [database setup](supabase/README.md). Refresh observations before assessment (a successful fetch cannot make delayed source measurements current):

```sh
python3 pythontest/api_requester.py --once
```

The CLI requires Supabase access even for its contextual inputs in explicit scenarios. The web dashboard's Demo feed runs entirely offline except for map tiles and does not contact Supabase.

The regular collector also fetches OpenTransportData road situations and Basel-area counter readings. It saves a combined source snapshot and counter-minute history alongside the existing per-source archives. For minute-by-minute traffic polling by itself, run:

```sh
python3 pythontest/opentransportdata.py --watch
```

Both paths use `OTD_TRAFFIC_SITUATIONS_API_KEY` and `OTD_TRAFFIC_COUNTERS_API_KEY` from the local `.env`. See [source notes](docs/SOURCES.md) for the geographic filter and its limits.

By default, the CLI prints a readable summary with the risk score and data coverage. Add `--output-format json` for the full structured observations and score components. Run a package-temperature scenario explicitly with:

```sh
PYTHONPATH=src python3 -m risk_assessment.cli --scenario hot --start-c 7 --duration-minutes 60 --tau-minutes 90
```

Run all simulated decision cases beside the current observed-data assessment with:

```sh
PYTHONPATH=src python3 -m risk_assessment.cli --scenario all
```

The Normal, Buffer, Expedite, Reroute, and combined cases use explicit simulated route/ETA evidence. The observed-data score appears separately. No map or GPS trace is required to exercise the decision logic.

Choose `--scenario cold` for a cold exposure, or use `--scenario observed-weather` to simulate package response to the latest MeteoSwiss air temperature from Supabase when the observation is no more than 30 minutes old. Stale or missing weather does not enter the observed-only score. Set `--ambient-c` to override the scenario ambient temperature. The package time constant is an illustrative input, not a qualified packaging property.

Run the calculation checks with:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

For shipment-specific observed planning, supply ETA and need-by timestamps with timezones, and explicit route evidence via `--route-status clear|disrupted|unknown`. Weather enters the score only with `--exposed-handling`; use `--controlled-handling` for a protected transfer. Without confirmed handling, weather stays context only. Map traffic counters to the route using repeated `--traffic-counter 'SITE|DIRECTION|LANE'` arguments, with exact identifiers from the source; a comparable historical baseline is still required. An alternative route requires `--alternate-route-available`, `--alternate-route-suitable`, and `--alternate-eta-at`; the alternate ETA must be earlier than the original and no later than material need-by. Suitability is explicitly supplied scenario/operator evidence, not inferred by a routing service.

Decision and System Suggestion share one policy. Missing essential shipment metadata produces Monitor; scores alone do not dispatch material. Observed-only logistics advice never authorizes product release.

Run the collector checks as well:

```sh
python3 -m unittest discover -s pythontest -p 'test_*.py'
```

## OpenTransportData route evidence

The default assessment displays the collected road candidate counts and includes their details in JSON. To score a detector you have verified is on the remaining shipment route, repeat `--road-counter 'SITE_ID|light|NORMAL_SPEED_KMH'` or use `heavy` for trucks. The normal speed must be a documented comparable reference, not an assumed speed limit. For example, `--road-counter 'CH:0006.01|light|80'` specifies an **illustrative operator assertion**, not a verified route or measured baseline provided by this repository.

For a reviewed event, use `--road-event 'EVENT_ID|restricted|SOURCE_UPDATED_AT'` or effect `disrupted`. Copy the exact version timestamp from `current_observations.road_traffic.traffic_situations` in JSON after checking its location, direction and vehicle applicability. Changed, expired, revoked, stale or unsupported event versions are excluded. These flags apply to observed mode (or the observed portion of `--scenario all`). An updated collector fetch is needed to add event version and validity metadata to older archives.

The terminal now reports the known score contribution and a range for missing evidence. See [calculation, applicability and limits](docs/risk-assessment.md#opentransportdata-road-evidence). Missing shipment route information remains unknown; no route or ETA is invented.

## Logistics dashboard

The frontend now shows environmental measurement cards, traffic messages, a selectable truck fleet, shipment details, temperature history, priority-score components and MapLibre routes. A visible switch selects Demo or Live evidence.

Use Python 3.10+ and the existing Node.js/npm setup. Build the frontend once:

```sh
cd frontend
npm ci
npm run build
cd ..
```

Start the dashboard server from the repository root:

```sh
PYTHONPATH=src python3 -m risk_assessment.server
```

On Windows PowerShell, use the launcher:

```powershell
./scripts/start-dashboard.ps1
```

If your Python executable has a different name or path, pass `-Python <interpreter>`. The Windows launcher keeps TLS verification enabled and uses the installed Git CA bundle when an MSYS Python build lacks a default certificate file. It changes only that process environment.

Open [the local dashboard](http://127.0.0.1:8000). The server uses Python's standard library and serves both the built frontend and `GET /api/dashboard`. It binds to loopback by default; this is a local demo server, not an authenticated public deployment. Starting the server also starts the existing collector with the same Python executable. It fetches sources immediately, then refreshes OpenTransportData road traffic every minute and the other sources every ten minutes, saving to Supabase when the local `.env` is configured. Both schedules share one collector process; slow requests can delay a poll. The Live screen polls every minute; its API response may stay cached for up to one minute. A fresh fetch cannot make an older source measurement current. The collector stops with the server. Use `--no-collector` when a separate collector is already running.

For frontend development, leave the backend running and start Vite in a second terminal:

```sh
cd frontend
npm run dev
```

Vite proxies `/api` to the backend on port 8000. For another API location, set the public `VITE_API_BASE_URL` in a local frontend .env and restart Vite. Keep database keys on the Python server. The shared browser contract is [interfaces.ts](frontend/src/interfaces.ts); the response validator is [dashboardData.ts](frontend/src/data/dashboardData.ts). The older `GET /api/map` contract remains supported.

### Present the demo

- Demo starts playing with four synthetic transports: urgent/stuck, normal, delayed with buffer, and a package-temperature deviation. Select a list item or map truck to inspect it.
- Replay advances one simulated minute per second. **Pause** freezes the clock; **Abspielen** resumes it. **Neustart** and scenario changes reset and start playback. After the replay finishes, **Abspielen** starts it again.
- The scenario selector provides normal operation, traffic with buffer, traffic with a critical deadline, temperature deviation and a suitable alternative route. In **BV-104 · Stau und Umleitung**, BV-104 switches to a connected street alternative after five simulated minutes; the dashed path then shows the original route. Its ETA, distance and production slack update together. The truck card, map legend and details retain an “Umleitung aktiv” label after the recommendation returns to Normal. Use **Routenunterschied ansehen** on the map to zoom to the streets where the paths differ; their shared prefix means the truck does not turn immediately at the route-switch time. The trigger is an explicit synthetic closure with a 45-minute delay, not observed live traffic. After switching, its original closure remains as an avoided incident/marker; active-route disruption counts exclude it. A temperature hold stops the affected demo truck while its synthetic temperature history continues; its ETA is planning-only.
- The backend reuses the existing thermal, priority and decision policy. Complete Demo evidence can yield 100% coverage; this is completeness of synthetic inputs, not scientific validation.
- Live reads all five environmental sources from Supabase and displays observation age/freshness. It has no truck GPS or package-temperature feed yet and therefore displays an empty shipment state. Live failures stay visible; they never substitute Demo data.
- Routes use cached full OSRM/OpenStreetMap driving geometry and MapLibre GL Directions. OSRM finds road paths; candidates are ranked by travel-time cost and a simulated closed road segment is excluded. A missing or slower/late alternative keeps the primary route. GPS, transport IDs, material, timing and temperatures are synthetic. The cache needs no routing connection during replay; map tiles need internet. These are car-profile paths without validated truck suitability or live traffic routing.

To refresh the committed street-route cache, run `python3 scripts/cache-demo-road-routes.py` from the repository root (internet required). This sends only the synthetic demo endpoints to the public OSRM service. Changing demo endpoints requires refreshing this cache.

Check the frontend with `npm test`, `npm run lint` and `npm run build` from frontend/. Backend/API replay checks are included in the existing root unittest command. Use `npm run format` to format the frontend.

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

Scenario package temperatures are simulated. Supabase weather is a regional observation, not a box sensor; traffic counts require a comparable route-counter baseline; and river restrictions require a matching ship-leg section. The model has no product-specific stability rules and cannot decide whether goods are safe or damaged. It is a planning demo, not an operational or quality-release system.

## Team

See [TEAM.md](TEAM.md) for GitHub usernames and working agreements.
