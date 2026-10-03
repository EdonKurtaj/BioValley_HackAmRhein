# Handoff: traffic polling cadence

Status: done · Updated: 2026-10-04 · Branch: fix/preserve-valid-port-import

## Goal
Refresh road traffic faster than its five-minute freshness allowance while keeping other source polling at its existing cadence.

## State
The existing collector uses one process and monotonic deadlines to schedule full cycles every ten minutes and traffic-only cycles every minute. This fix shares the Port-import branch at the user's request. All 105 backend tests and 59 collector tests pass.

## Done
- Added minute-by-minute traffic refresh between full cycles, reusing archive, ingestion and retry paths.
- Kept the existing five-minute counter freshness allowance and source measurement timestamps.
- Traffic-only cycles skip Port transformation and other source requests.
- Verified scheduling with simulated collection duration and a temporary failure; later polls continue without interval drift.
- All 59 collector tests pass. Whitespace checks pass.
- Updated run instructions and source documentation.

## Next
1. Restart any running dashboard backend/collector to load the new scheduling code.
2. Review and merge only after explicit approval.

## Files
- `pythontest/api_requester.py`: scheduling and traffic-only cycles.
- `pythontest/test_api_loop.py`: cadence, error recovery and ingestion regressions.
- `src/risk_assessment/config.py`: updated polling comment; freshness values unchanged.
- `README.md`, `pythontest/README.md`, `docs/SOURCES.md`: run behavior.

## Decisions made
Use the existing collector process so there is no additional writer competing for the same retry outbox. Use the existing branch for the second and third fixes.

## Open questions / problems
- Slow network/database requests can delay scheduled polls; stale source measurements remain excluded.

## Resume prompt
> Read handoff/fix-traffic-polling-cadence.md and continue on fix/preserve-valid-port-import. Do not create another branch for this fix.
