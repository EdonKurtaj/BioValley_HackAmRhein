# Handoff: automatic Live refresh

Status: in progress · Updated: 2026-10-03 21:34 · Branch: main (uncommitted) · Last owner: @Elton53

## Goal
Keep Live environmental observations refreshed when the local dashboard server is running.

## State
The server now launches the existing collector with its own Python interpreter. The collector fetches immediately, then uses its existing ten-minute watch interval, and stops with the server. A separate collector can be used with `--no-collector`. Changes are local and uncommitted because task-branch creation was denied earlier.

## Done
- Reused the existing collector and Supabase ingestion path; no new data writer or dependency.
- Added mocked server-start and child-process lifecycle tests. Root tests (102), collector tests (57), server command check, and strict documentation check passed.
- Ran the collector once against all six public sources; all six fetches and Supabase writes succeeded. The running Live API then returned MeteoSwiss 21:20 Europe/Zurich, 16.9 °C, freshness current.
- Updated the run instructions, design, and team decision log.

## Next
1. Restart the local dashboard backend to load the new server behavior; verify the next source observation in Live mode.
2. If task-branch creation is later permitted, run the privacy guard and commit on that branch. Do not commit to main.

## Files
- `src/risk_assessment/server.py`: collector lifecycle tied to dashboard server.
- `tests/test_dashboard.py`: automatic start and stop checks.
- `README.md`, `docs/design.md`, `docs/decisions.md`: startup behavior and rationale.

## Decisions made
Reuse the collector's existing watch mode and interval; leave source freshness based on measurement time rather than fetch time.

## Open questions / problems
- Live freshness still depends on upstream source publication and working local API/Supabase settings.

## Resume prompt
> Continue automatic Live refresh. Read handoff/fix-auto-live-refresh.md, finish checks, restart the backend, and verify the Live timestamp.
