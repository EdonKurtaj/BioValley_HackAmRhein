# Traffic-only Supabase ingestion

## State

Done on `feat/local-risk-assessment`. The user applied the source-kind migration in Supabase, and live delivery was verified.

## Done

- Confirmed live Supabase rejection: HTTP 400, PostgreSQL 23514, `data_sources_source_kind_check`. The existing database does not allow `opentransportdata` yet.
- Wired standalone `opentransportdata.py` single runs and watch mode into the same archived fetch result and durable Supabase outbox as the regular collector. Added `--local-only`.
- Kept numeric counter flow/speed in `observations`, with source measurement times and stable identities. Kept situation messages in `fetch_runs.raw_payload`.
- Added a safe, actionable migration hint for this specific database constraint error, without printing response details or credentials.
- Made the existing migration transactional; did not change `schema.sql`.
- Covered delivery, failed-fetch logging, database retry, observation identity and sanitized errors. Updated the archive test to mock the newly added traffic source without making network requests.
- Validation: 56 collector tests and 60 engine/integration tests pass. Live traffic pull returned 176 situations, 329 sites and 328 current readings; the pending batch remains in the local outbox after the database rejection.

## Next

1. Restart any existing traffic watcher to load the new ingestion code.
2. The new feed is not yet wired into risk scoring; route matching and comparable baselines are separate work.

## Live acceptance

- The pending batch delivered successfully: 946 observations and its fetch log.
- REST read-back confirmed vehicle-flow values in vehicles/hour and speeds in km/h at the source measurement time, with a successful fetch log and no error.
- The durable outbox is empty after successful delivery.
- Commit `c6f8c02` remains local because the user declined the push.
