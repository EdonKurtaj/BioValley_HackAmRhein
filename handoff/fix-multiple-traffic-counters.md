# Handoff: multiple route traffic counters

Status: done · Updated: 2026-10-04 · Branch: fix/multiple-traffic-counters

## Goal
Prevent a newer normal counter from hiding an anomaly at another selected route counter.

## State
Per-counter evaluation and conservative aggregation are implemented and verified. The fix is on its own branch; merging into main remains pending. The other review findings are unchanged.

## Done
- Reproduced the bug with a high-volume counter A and newer normal counter B.
- Evaluate each selected counter against its own comparable history and freshness.
- Use the strongest valid anomaly; missing evidence remains unknown below the anomaly threshold.
- Added regression cases for ordering, missing/stale counters and score/action integration.
- Updated the calculation documentation.
- All 108 backend tests (including six new regression tests), 57 collector tests and the whitespace check pass.

## Next
1. Review the fix branch. Merge requires explicit approval.

## Files
- `src/risk_assessment/disturbance.py`: evaluate and aggregate route counters.
- `tests/test_multiple_traffic_counters.py`: regression and integration checks.
- `docs/risk-assessment.md`: aggregation and missing-evidence behavior.

## Decisions made
Retain the existing traffic anomaly threshold and score formula; missing counters cannot lower an independently confirmed saturated traffic signal.

## Open questions / problems
- The other findings from the project review remain outside this fix.

## Resume prompt
> Read handoff/fix-multiple-traffic-counters.md and verify the fix branch. Do not merge without explicit approval.
