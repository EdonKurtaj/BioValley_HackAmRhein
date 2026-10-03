# Basel cold-chain risk prototype

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

This prototype explores how weather, traffic, and Rhine signals can inform cold-chain logistics planning for a generic refrigerated material. Package-temperature scenarios and observed local conditions are separate evidence.

## The problem

A Basel-area factory needs a critical refrigerated material on time while preserving its 2–8 °C handling conditions. This demo combines public environmental measurements with explicit shipment context to explain planning recommendations.

## How to run it

From the repository root, run the latest saved open-data observations only. By default, the risk assessment reads MeteoSwiss weather rows from Supabase; Rhine and traffic context still come from the collector's local archives. This does not simulate package temperature, traffic, or ETA:

```sh
PYTHONPATH=src python3 -m risk_assessment.cli
```

The collector keeps local archives and stores measurements in Supabase when the local `.env` is configured. The assessment selects the newest MeteoSwiss station batch from `observations` and checks freshness from its source `observed_at` timestamp. Decision persistence is not implemented. See [collector setup](pythontest/README.md) and [database setup](supabase/README.md). Refresh observations before assessment (a successful fetch cannot make delayed source measurements current):

```sh
python3 pythontest/api_requester.py --once
```

For an offline assessment using the local weather archive, pass `--weather-source local`. This changes only the weather input; traffic, Rhine and road evidence keep using their existing archive paths.

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

Choose `--scenario cold` for a cold exposure, or use `--scenario observed-weather` to simulate package response to the latest MeteoSwiss air temperature from the selected weather store when the observation is no more than 30 minutes old. Stale or missing weather does not enter the observed-only score. Set `--ambient-c` to override the scenario ambient temperature. The package time constant is an illustrative input, not a qualified packaging property.

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

## React map frontend

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

### Connect a backend

The single shared map contract is [frontend/src/interfaces.ts](frontend/src/interfaces.ts); HTTP response validation and demo data live in [the adapter](frontend/src/data/mapData.ts). Serve `GET /map` under your API base URL using that JSON contract. Then create a local `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api
```

Restart Vite after changing it. The frontend requests `http://localhost:8000/api/map`. For a separate origin, the backend must allow the frontend origin through CORS. All `VITE_` values are public browser configuration: never use credentials here. For deployment, supply the API URL when building and use HTTPS or a same-origin `/api` reverse proxy. Keep backend responses compatible with the contract to avoid UI changes.

Backend failures remain visible with a retry action. The map itself stays available even if the location API is unavailable. The existing [Python requester and database setup](supabase/README.md) remain independent; connecting their results to the map endpoint is a future task.

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

Scenario package temperatures are simulated. Supabase weather is a regional observation, not a box sensor; the current ten-record traffic sample is not a route baseline; and river restrictions require a matching ship-leg section. The model has no product-specific stability rules and cannot decide whether goods are safe or damaged. It is a planning demo, not an operational or quality-release system.

## Team

See [TEAM.md](TEAM.md) for GitHub usernames and working agreements.
