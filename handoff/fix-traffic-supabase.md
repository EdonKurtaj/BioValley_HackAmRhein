# Traffic-only Supabase ingestion

## State

Code implemented and tested on `feat/local-risk-assessment`. Live database delivery awaits execution of the existing source-kind migration in Supabase; no SQL administration connection is configured locally.

## Done

- Confirmed live Supabase rejection: HTTP 400, PostgreSQL 23514, `data_sources_source_kind_check`. The existing database does not allow `opentransportdata` yet.
- Wired standalone `opentransportdata.py` single runs and watch mode into the same archived fetch result and durable Supabase outbox as the regular collector. Added `--local-only`.
- Kept numeric counter flow/speed in `observations`, with source measurement times and stable identities. Kept situation messages in `fetch_runs.raw_payload`.
- Added a safe, actionable migration hint for this specific database constraint error, without printing response details or credentials.
- Made the existing migration transactional; did not change `schema.sql`.
- Covered delivery, failed-fetch logging, database retry, observation identity and sanitized errors. Updated the archive test to mock the newly added traffic source without making network requests.
- Validation: 56 collector tests and 60 engine/integration tests pass. Live traffic pull returned 176 situations, 329 sites and 328 current readings; the pending batch remains in the local outbox after the database rejection.

## Next

1. Execute `supabase/migrations/20261003190000_allow_opentransportdata_source_kind.sql` in this project's Supabase SQL Editor. The user has been asked to do this.
2. Flush pending batches using the existing Supabase ingestor, then verify `fetch_runs` and `observations` for source `opentransportdata_basel_region` through the REST API.
3. Restart any existing traffic watcher to load the new ingestion code. The new feed is not yet wired into risk scoring; this task concerns storage.
