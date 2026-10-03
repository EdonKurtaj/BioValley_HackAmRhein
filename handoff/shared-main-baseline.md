# Shared main baseline

## State

Integration verified on `chore/shared-main-integration`, ready for the user-authorized promotion to main.

## Included

- Reviewed `feat/local-risk-assessment`, including the transport-evidence review, package-temperature safeguards, traffic Supabase ingestion and durable retry outbox.
- `origin/feat/basel-react-map` at `0031c8e`: standalone React/TypeScript/Vite/MapLibre map, API adapter and contracts, styles, tests and documentation.
- Challenge text from the weather branch and TEAM.md from the setup branch. Older collector/transformer implementations and the superseded plan were not copied over the current implementation.
- README retains both Python and frontend startup commands. No browser-side database key was added.

## Verification

- 80 risk/integration tests, 57 collector tests and 9 frontend tests pass (146 total).
- Frontend TypeScript/Prettier checks and production build pass under Node.js 24. The map library produces a non-blocking bundle-size warning.
- Browser verified map rendering, filtering and location selection; examples remain clearly labelled.
- CLI all-scenario JSON, documentation and whitespace checks pass.
- Supabase directory, collector and risk source files are identical to the working local-risk-assessment baseline. No SQL migration was executed as part of this integration.
- Live read-only REST checks confirmed all six registered sources, traffic observations and a successful traffic fetch with no error.

## Next

- Team members update their local main and create their next feature branch from it. Keep each participant's .env and profile local.
- The map still displays example locations. Exposing risk results through a server-side API and displaying them in the frontend remains separate work.
- Numeric observation and fetch-log ingestion remains active; risk decisions are not yet persisted to Supabase.
