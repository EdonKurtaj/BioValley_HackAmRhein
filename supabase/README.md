# Basel supply-risk database

Apply [`schema.sql`](schema.sql) in the Supabase SQL Editor. It creates the tables and read policies for the dashboard. Ingestion should use a server-side Supabase secret key; never put that key in browser code or commit it.

## What the requester fetches

`pythontest/api_requester.py` makes five GET requests on each cycle:

| Source ID | What is fetched | Best fit in this schema |
| --- | --- | --- |
| `meteoswiss_basel_temperature` | Current Basel/Binningen (BAS) air temperature `tre200s0` in °C, observation time, station metadata, age at fetch, and parameter metadata | A `fetch_runs` row plus an `observations` row (`metric = tre200s0`, station `BAS`) |
| `basel_dataset_100006` | JSON records from Basel motor traffic API, limited to latest 10 records ordered by `datetimefrom` | Preserve the complete response in `fetch_runs.raw_payload`; normalize each traffic count and vehicle class into `observations` |
| `basel_dataset_100089` | JSON records from Basel Rhine API, limited to latest 10 records ordered by `timestamp` | Preserve the response; normalize water level and discharge into `observations` |
| `port_pegel_current` | Port page headings, tables and visible text; raw HTML is also saved locally | Preserve extracted page content in `fetch_runs.raw_payload`; normalize gauge levels / navigation status into `observations` when parsed |
| `port_pegel_forecast` | Forecast page headings, tables and visible text; raw HTML is saved locally | Preserve extracted page content; store forecast values as observations with their forecast valid time in `observed_at` |

Every request also produces operational metadata: fetch time, HTTP status, success flag, rate-limit flag, retry hint, response size, error, and (when present) `Last-Modified`. Those belong in `fetch_runs`, including failed requests. Source responses remain in JSONB so parser changes do not discard fields that the first dashboard does not use.

## Tables and flow

1. `data_sources` catalogs the five inputs.
2. `fetch_runs` records one attempted request and its untouched parsed response per source and cycle.
3. `observations` stores one normalized metric per station/time, with a stable source-specific `observation_key` for idempotent upserts and `raw_record` for traceability.
4. `materials`, `material_lots`, and `shipments` represent the at-risk inventory and replenishment context.
5. `manufacturing_decisions` stores the action (`normal`, `buffer`, `expedite`, `reroute`, or `quality_review`), explanation, validity, and evidence references. It deliberately stores no unvalidated 0–100 risk score.

The challenge assumes 2–8 °C handling for its example material, so these are demo defaults on `materials` and `material_lots`. WHO TRS 961 Annex 9 supports tracking, receipt checks, transport monitoring, and quarantine of suspect products; this prototype schema records those decisions but does not implement a regulated quality system or determine product disposition.

## Collection limits to account for

The requester currently saves to local JSON/JSONL only; it does not write to Supabase yet. It asks each Basel API for just 10 latest records on each 10-minute cycle. The Rhine dataset is described by the challenge as five-minute data, so this is a rolling recent sample rather than complete history and could leave gaps. Increase the API page size or fetch incrementally before relying on long-window anomaly detection. The current MeteoSwiss source fetches only one temperature metric, not the full weather set (rain, wind, humidity, radiation).

The API requester does not show the expanded Basel field definitions in its source code, so source-specific normalization should map the live response field names into `metric`, `value`, `unit`, and `dimensions`; the original JSON remains available in `raw_payload` and `raw_record`.

## Access

Row-level security is enabled. Anonymous and signed-in clients can read the public data-source catalog and open-data observations. Materials, lots, shipments, and decisions have no client read policy or grant; keep them server-side until a tenant-aware authenticated access design is implemented. Ingest and decision writes belong in trusted server-side code using `SUPABASE_SECRET_KEY`; never place that key in browser code or commit it.
