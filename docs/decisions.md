# Decisions

One line per decision, newest at the bottom. Never edit an old line; add a new one that says what it replaces.

Format: `- <date> · <decision> · @<github-username> · Affects: <tasks or areas> · Why: <short> · Instead of: <alternative, why not>`

- 2026-10-03 · Implement the local risk engine in Python with shared contracts in `src/risk_assessment/interfaces.py`; report explainable actions and keep product/tenant data service-side in Supabase without a numeric risk score · @gggnnnttt · Affects: risk calculations and Supabase schema · Why: temperature and route evidence are not validated probability inputs, and customer shipment data must not be anonymously readable · Instead of: a single 0–100 score and public demo-table reads.
- 2026-10-03 · Exercise the full open-data-to-decision flow in a local terminal dashboard with explicit simulated route/ETA cases · @gggnnnttt · Affects: demo pipeline · Why: decision logic can be validated before GPS simulation, MapLibre, or a web dashboard is available · Instead of: presenting simulated route events as live public-data findings.
- 2026-10-03 · Add a 0–100 weighted manufacturing-priority index with visible component scales and missing-data bounds; keep quality review as a separate package-evidence rule, replacing the earlier no-score decision · @gggnnnttt · Affects: local risk calculation and dashboard · Why: the challenge explicitly asks for a manufacturing risk score and for combined signals to increase priority, while available data cannot justify a product-damage probability · Instead of: omitting the challenge's score or presenting it as validated product risk.
