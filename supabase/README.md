# Basel supply-risk database

The collector writes to the existing `data_sources`, `fetch_runs`, and `observations` tables defined in [`schema.sql`](schema.sql). These tables must already exist in Supabase. HTTP 404/PGRST205 means the table is absent from the exposed schema; the collector cannot create tables through the data REST API. The schema file is unchanged by this integration.

Configure `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in the project's local `.env`; see [the variable template](../.env.example). The collector supports current secret keys and legacy service-role JWTs and never prints credentials. Run it with the [requester commands](../pythontest/README.md). No additional package installation is required.

## What the requester fetches

`pythontest/api_requester.py` makes five GET requests on each cycle:

| Source ID | What is fetched | Best fit in this schema |
| --- | --- | --- |
| `meteoswiss_basel_temperature` | Nine current Basel/Binningen (BAS) weather metrics, observation time, station metadata, age at fetch, and parameter metadata | A fetch log plus one observation per available weather metric; units and aggregation windows come from [weather_parameters.py](../pythontest/weather_parameters.py) |
| `basel_dataset_100006` | JSON records from Basel motor traffic API, limited to latest 10 records ordered by `datetimefrom` | Each count field is its own metric in vehicles; station, lane, direction, interval end and traffic type distinguish observation identities |
| `basel_dataset_100089` | JSON records from Basel Rhine API; window documented in [data notes](../docs/data-notes.md) | `abfluss` in m3/s, `pegelhoehe` in cm, and `pegel` in m; observation time comes from `timestamp` |
| `port_pegel_current` | Port page headings, tables and visible text; raw HTML is also saved locally | Gauge readings become `water_level` in the published units and Europe/Zurich observation time; flood thresholds remain in the raw payload |
| `port_pegel_forecast` | Forecast page headings, tables and visible text; raw HTML is saved locally | `water_level_m_above_sea_level` in m and `discharge_m3_per_second` in m3/s; valid time is `observed_at`, with issue time and forecast flag in `dimensions` |

Every request also produces operational metadata: fetch time, HTTP status, success flag, rate-limit flag, retry hint, response size, error, and (when present) `Last-Modified`. Those belong in `fetch_runs`, including failed requests. Source responses remain in JSONB so parser changes do not discard fields that the first dashboard does not use.

## Tables and flow

1. `data_sources` catalogs the five inputs.
2. `fetch_runs` records one attempted request and its untouched parsed response per source and cycle.
3. `observations` stores one normalized metric per station/time, with a stable source-specific `observation_key` for idempotent upserts and `raw_record` for traceability.
4. `materials`, `material_lots`, and `shipments` represent the at-risk inventory and replenishment context.
5. `manufacturing_decisions` stores the action (`normal`, `buffer`, `expedite`, `reroute`, or `quarantine`), 0–100 risk score, explanation, validity, and evidence references. The risk engine currently reads local collector snapshots; it does not write decisions to this table. Its `monitor`/`quality_review` actions and score intervals require an explicit future persistence contract rather than silently mapping them to this legacy schema.

The challenge assumes 2–8 °C handling for its example material, so these are demo defaults on `materials` and `material_lots`. WHO TRS 961 Annex 9 supports tracking, receipt checks, transport monitoring, and quarantine of suspect products; this prototype schema records those decisions but does not implement a regulated quality system or determine product disposition.

## Collection limits to account for

Each new source attempt produces a `fetch_runs` row, including HTTP/network errors and unexpected source exceptions. Only successful responses produce observations. A normalization failure is recorded in the fetch's error field alongside the unchanged raw payload. It does not stop the remaining sources. All timestamps sent to Supabase use UTC; values retain their original units. Ambiguous local times at DST transitions are reported rather than guessed. The forecast page's explicit MEWZ/HHEC timezone is UTC+01:00, including during summer.

Before transmission, each new attempt and its observations are written atomically to `.hack/ingest-outbox/`. Database failures keep that batch pending; the next cycle retries pending batches before fetching again. A stable UUID makes repeated `fetch_runs` delivery idempotent. Observation upserts use `(source_id, observation_key, metric)`; traffic lanes remain separate and forecast issues retain separate identities. A batch is removed only after all database writes succeed. Writes to fetch_runs and observations are separate REST requests; the fetch can become visible before all observations have arrived.

The existing local JSON/JSONL/HTML archives remain active. No historical files are backfilled; retries concern only new attempts captured by this integration. If the local disk cannot save a pending batch, the collector reports the storage failure and continues, but automatic database retry cannot be guaranteed for that attempt. The rolling source windows remain limited; see [data request notes](../docs/data-notes.md).

The ingestion contracts live in [interfaces.py](../pythontest/interfaces.py), mappings in [normalize_observations.py](../pythontest/normalize_observations.py), and delivery/retry logic in [supabase_ingest.py](../pythontest/supabase_ingest.py).

## Access

Row-level security is enabled. The existing schema allows public reads of open data and demo factory tables. The separate [factory-access migration](migrations/20261003160000_restrict_factory_client_access.sql) removes client access to materials, lots, shipments and decisions while preserving collector access and public open-data reads. Apply this migration in Supabase before storing confidential factory data. It tolerates absent factory tables and is repeatable. The migration is prepared locally and is not automatically applied by the collector. Keep ingest writes in trusted server-side code using `SUPABASE_SECRET_KEY`; never place it in browser code or commit it.
