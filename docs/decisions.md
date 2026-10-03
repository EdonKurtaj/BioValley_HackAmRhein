# Decisions

One line per decision, newest at the bottom. Never edit an old line; add a new one that says what it replaces.

Format: `- <date> · <decision> · @<github-username> · Affects: <tasks or areas> · Why: <short> · Instead of: <alternative, why not>`

- 2026-10-03 · Implement the local risk engine in Python with shared contracts in `src/risk_assessment/interfaces.py`; report explainable actions and keep product/tenant data service-side in Supabase without a numeric risk score · @gggnnnttt · Affects: risk calculations and Supabase schema · Why: temperature and route evidence are not validated probability inputs, and customer shipment data must not be anonymously readable · Instead of: a single 0–100 score and public demo-table reads.
