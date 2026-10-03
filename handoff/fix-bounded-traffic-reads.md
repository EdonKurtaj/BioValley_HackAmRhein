# Handoff: bounded traffic reads

Status: done · Updated: 2026-10-04 · Branch: fix/preserve-valid-port-import

## Goal
Stop live traffic requests from downloading the full observation history while retaining useful route-specific baselines.

## State
Traffic context is limited to 100 total-count observations. Explicit CLI route counters trigger separate filtered latest-value and comparable-baseline queries, with at most 52 older comparable observations per counter. All 110 backend tests and 59 collector tests pass. This shares the branch with the second and third fixes.

## Done
- Removed the unbounded default from the observation reader.
- Avoided loading historical traffic for dashboard requests without route mappings.
- Filtered station, direction, lane, weekday and hour in Supabase before applying baseline limits.
- Wired CLI route-counter mappings into source loading and retained per-invocation caching.
- Added five tests including a 1,500-row unrelated archive, selected counters outside the context window, bounded comparisons and insufficient history.
- Updated database and assessment documentation.

## Next
1. Review before merging; merge requires explicit approval.
2. Restart a running backend to load the new reader.

## Files
- `src/risk_assessment/supabase_data.py`: bounded, targeted traffic reads.
- `src/risk_assessment/cli.py`: pass explicit route-counter mappings.
- `tests/test_bounded_traffic_reads.py`: archive-size and baseline regressions.
- `supabase/README.md`, `docs/risk-assessment.md`: query limits and baseline behavior.

## Decisions made
Use the newest 52 comparable historical observations as the bounded prototype baseline; keep the existing minimum sample count and freshness policy. Archive contents remain untouched.

## Open questions / problems
- Remote Supabase latency and query plans have not been benchmarked; tests use a simulated database.
- The first multiple-counter fix remains on its separate branch.

## Resume prompt
> Read handoff/fix-bounded-traffic-reads.md and continue on fix/preserve-valid-port-import. Do not create another branch for this fix.
