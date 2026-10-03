# Collector and risk-engine integration

## State

Implementation done on `feat/local-risk-assessment`; main is unchanged.

## Done

- Integrated `origin/main` collector, local archives, durable Supabase outbox, all five sources and nine verified weather metrics with risk-review fixes 1–6.
- Resolved the MeteoSwiss conflict in favor of the maintained collector and its verified metadata, retaining the risk precipitation regression test.
- Preserved `supabase/schema.sql` exactly as on `origin/main`. Factory access restrictions are a separate conditional migration and have not been applied to a database.
- Retained local risk contracts, package-history safeguards, measurement-time freshness, one shipment-aware decision policy and centralized priority weights.
- Removed references to pressure from current-weather output because this collector does not request pressure. Legacy traffic/Rhine snapshots with `data: null` remain unknown without crashing.
- Added four integration tests for shared nine-metric values, preserved last-good data after network failure, stale measurements after fresh fetch, and legacy null snapshots.
- Validation: 51 collector tests and 60 engine/integration tests pass; documentation and whitespace checks pass.

## Next

- Restart any running collector to load the integrated code; run `python3 pythontest/api_requester.py --once`, then `PYTHONPATH=src python3 -m risk_assessment.cli`.
- Apply the separate factory-access migration in Supabase when appropriate; SQL execution has not been verified against a live database.
- Review and approve the feature branch before merging it into main.
- Decision persistence remains a future task: `monitor`/`quality_review` and score intervals need an explicit storage contract. The current engine reads local snapshots, while measurements and fetch attempts go to Supabase.
