# Decisions

One line per decision, newest at the bottom. Never edit an old line; add a new one that says what it replaces.

Format: `- <date> · <decision> · @<github-username> · Affects: <tasks or areas> · Why: <short> · Instead of: <alternative, why not>`

- 2026-10-03 · Add collector ingestion contracts in pythontest/interfaces.py; normalize five sources and use the existing Supabase uniqueness constraints with a durable local outbox · @EdonKurtaj · Affects: collector, fetch_runs, observations · Why: retain every new attempt and avoid duplicate measurements after retries · Instead of: schema changes or historical backfill, outside this task.
- 2026-10-03 · Extend the existing MeteoSwiss source to nine weather metrics with centrally verified units and aggregation windows; preserve its source ID and skip missing values during ingestion · @EdonKurtaj · Affects: collector, weather observations · Why: provide ambient weather context while preserving the existing temperature series · Instead of: another source or schema change, unnecessary for the available CSV fields.
