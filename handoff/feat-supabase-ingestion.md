# Supabase collector ingestion

## State
Done: local implementation and live Supabase delivery verified. The user applied the prepared collector-table SQL; all three tables are reachable. schema.sql remains unchanged. No commit or push.

## Done
- Inspected saved payloads and existing schema; confirmed Rhine units against public dataset metadata.
- Added shared ingestion interfaces and a decision line.
- Added source-specific UTC normalization, stable observation keys, REST writes, and a local retry outbox under .hack/.
- Collector writes each attempt independently of local archive success; source and database failures do not stop polling.
- All 46 offline regression tests pass; compileall, git diff --check, and doc-check pass. The 19 ingestion tests also pass with ResourceWarning treated as an error.
- Partial-write replay preserves fetch UUIDs and observation identities without duplicates; secrets are excluded from error messages.
- Updated the connection-check script to check the actual three tables without a third-party SDK.
- Documented configuration, mappings, UTC timezones, source limits, and retry behavior. Added an empty .env.example.
- Prepared /private/tmp/supabase-collector-setup.sql by copying only the existing collector table definitions and indexes, enabling RLS, and retaining service-role access. It adds no inventory/risk tables or public read policies. Opened this SQL file in Codex and asked the user to run it in their Supabase SQL Editor.
- After the user applied the SQL, the connection check succeeded for data_sources, fetch_runs, and observations.
- Live --once succeeded for all five sources and wrote five fetch_runs plus 801 observations: MeteoSwiss 1, traffic 120, Rhine 144, current port 6, forecast port 530.
- Read back each source's rows and verified values, units, stable keys, and fetch references. Replayed identical batches: no additional observations or fetch_runs appeared. Retry outbox is empty.

## Next
- Collector is ready: python3 pythontest/api_requester.py --once for one cycle, or omit --once for watch mode.
- No historic archives should be backfilled. Only new attempts and queued retries are in scope.
- Review local changes and create a branch when authorized; run privacy hooks before committing.

## Scope
No schema.sql edits, historical backfill, risk engine, seed inventory, frontend, or authentication changes.
