# Supabase weather in risk assessment

## State
Done on `main` per the team's explicit shared-branch decision. Working-tree changes are uncommitted.

## Done
- Confirmed live Supabase has 73 Basel/Binningen MeteoSwiss rows; newest observation timestamp was `2026-10-03T15:40:00+00:00` and it included all nine metrics (temperature, precipitation, radiation, sunshine, mean/gust wind, humidity, dew point, wind direction).
- Added a read-only server-side PostgREST reader selecting the newest same-timestamp batch for station `BAS`.
- Made Supabase the default weather source for observed and demo CLI runs; freshness continues to use MeteoSwiss `observed_at`. Added explicit `--weather-source local` fallback.
- Threaded the chosen weather snapshot through scoring and weather-disturbance output; no frontend credentials or Supabase schema changes.
- Added provider and assessment regression tests, and updated README/risk model/decision docs.
- Verified the live CLI against Supabase. The latest sample returned 22.2 °C, 0 mm/10 min precipitation, 11.5 km/h gust, plus the other six fields; it was about 23 minutes old. With `--exposed-handling`, weather is counted as 1/4 evidence groups and contributes 0/40 under those normal observed conditions. Without handling confirmation it remains visible context only.
- Risk tests: 83 passed. Collector tests: 57 passed. Compileall, doc-check and `git diff --check` passed.

## Next
- Review the uncommitted changes and commit/push only after the team's privacy guard and normal GitHub workflow.
