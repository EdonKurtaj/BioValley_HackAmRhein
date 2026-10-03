# Handoff: code correctness review

Status: in progress · Updated: 2026-10-03 21:12 · Branch: main (uncommitted) · Last owner: @Elton53

## Goal
Review the repository for correctness and documentation drift, then fix confirmed issues.

## State
Local fixes are ready and verified, including the strict documentation check. Creating a task branch was denied, so changes remain uncommitted on main; nothing was pushed or merged.

## Done
- Rejected future weather and traffic timestamps as current evidence, including when an archived weather age says zero; added regression tests.
- Kept Rhine marks and weather warning onsets in shared config so dashboard and risk calculations agree.
- Paused demo replay on restart and feed changes.
- Corrected stale design and CLI data-source documentation.
- Made Prettier accept native Windows line endings. Root Python tests (100), collector tests (57), frontend tests (18), frontend lint, and production build passed.

## Next
1. If branch creation is later permitted, move these changes to a task branch, run the privacy guard, then commit them. Do not commit directly to main.

## Files
- `src/risk_assessment/local_data.py`, `src/risk_assessment/disturbance.py`: source timestamp freshness.
- `src/risk_assessment/config.py`, `src/risk_assessment/logistics.py`, `src/risk_assessment/observed.py`, `src/risk_assessment/dashboard.py`: shared warning thresholds.
- `frontend/src/App.tsx`, `frontend/.prettierrc.json`: replay and formatting.
- `tests/test_dashboard.py`, `tests/test_risk_assessment.py`: regression checks.
- `docs/design.md`, `docs/risk-assessment.md`: current behavior.

## Decisions made
Retained the existing reroute policy after its contract tests showed it intentionally allows a verified route restriction to trigger route advice before handling context is known.

## Open questions / problems
- Branch creation needs permission; no commit or push has been made.

## Resume prompt
> Continue the correctness review. Read handoff/fix-review-correctness.md, inspect the verified diff, and only create a branch if permitted.
