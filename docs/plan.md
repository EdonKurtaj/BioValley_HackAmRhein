# Risk-assessment plan

Goal: use current observed Basel weather, traffic and Rhine data plus clearly labelled simulated shipment telemetry to explain risk to a critical generic 2–8 °C material. Keep thermal exposure separate from route/supply disruption, combine supported signals in an explainable prototype manufacturing-priority index, and keep product-quality disposition with quality review because no product-specific stability limits are provided. The calculation and assumptions are in [risk-assessment.md](risk-assessment.md).

Owners are proposed as @gggnnnttt because no team ownership file is present. Reassign when the team agrees. Do not treat simulated telemetry or demo thresholds as validated operational controls.

## M1 — Make inputs and assumptions trustworthy

### In order

#### T1 Audit and retain the API inputs
Owner: @gggnnnttt (proposed)  
Needs: nothing  
Files: `pythontest/api_requester.py`, `docs/data-signals.md`, `docs/SOURCES.md`  
Done when: each source’s timestamp, unit, geographic scope, freshness and missing-value behavior are documented; the audit states which source snapshots are observed and that Port forecasts are excluded from this no-forecast risk calculation.

#### T2 Retrieve a traffic baseline for route counters
Owner: @gggnnnttt (proposed)  
Needs: T1  
Files: `pythontest/api_requester.py`, `pythontest/data/` (local sample output), `docs/data-signals.md`  
Done when: selected route counter(s) have a documented multiweek hourly baseline by site, direction and relevant vehicle class; the approach handles weekday/hour seasonality and the dataset’s daylight-saving behavior. Keep a small redistributable sample only if permitted.

### Parallel after T1

#### T3 Confirm traffic-class and route mapping
Owner: @gggnnnttt (proposed)  
Needs: T1  
Files: `docs/risk-assessment.md`, `docs/data-signals.md`  
Done when: chosen MIV counter(s) have verified coordinates, direction/lane meaning and class coverage; the plan states that counts signal volume anomalies but do not by themselves measure congestion or travel time.

## M2 — Calculate explainable thermal and logistics risk

### In order

#### T4 Define shipment scenario inputs
Owner: @gggnnnttt (proposed)  
Needs: T1  
Files: `docs/risk-assessment.md`, shared interface/model file once selected  
Done when: a demo shipment can specify material start temperature (2, 5 or 7 °C), 2–8 °C bounds, box temperature series or simulated ambient exposure, sensor quality, handling stops, truck/ship legs, planned need time and production slack.

#### T5 Calculate box-temperature exposure
Owner: @gggnnnttt (proposed)  
Needs: T4  
Files: thermal calculation module, its focused tests, `docs/risk-assessment.md`  
Done when: sensor readings produce hot/cold minutes, peaks and degree-hours; gaps and sensor uncertainty are visible; simulated thermal response uses an explicit adjustable package time constant and is labelled illustrative, not product quality evidence.

### Parallel after T4

#### T6 Detect traffic and Rhine route disruption
Owner: @gggnnnttt (proposed)  
Needs: T2, T3, T4  
Files: route-risk module, its focused tests, `docs/risk-assessment.md`  
Done when: traffic anomaly compares like-for-like site/direction/time baselines; river status applies only to a simulated ship segment and uses official high-water restrictions; low-water thresholds are not invented; any ETA/slack comes from simulated tracking, not raw vehicle counts.

#### T7 Join weather to handling windows
Owner: @gggnnnttt (proposed)  
Needs: T1, T4  
Files: weather-risk module, its focused tests, `docs/data-signals.md`  
Done when: temperature, rain, radiation, wind and humidity affect only scenario-relevant exposed handling/route contexts; missing or stale station data becomes unknown; weather is not presented as package temperature or forecast.

#### T8 Turn signals into actions
Owner: @gggnnnttt (proposed)  
Needs: T5, T6, T7  
Files: decision module, its focused tests, `docs/risk-assessment.md`  
Done when: the displayed logic can explain Normal → Buffer → Expedite → Reroute, with quality review/quarantine taking precedence for out-of-range or uncertain package telemetry; it shows thermal exposure and route slack separately and names the triggering evidence.

## M3 — Demonstrate and bound the result

### In order

#### T9 Replay the six scenario cases
Owner: @gggnnnttt (proposed)  
Needs: T5, T6, T7, T8  
Files: `pythontest/data/` or demo fixtures, focused tests, `docs/risk-assessment.md`  
Done when: hot start-at-7, cold start-at-2, rainy outdoor handoff, traffic spike, Rhine high-water ship restriction, and stale/missing telemetry each produce the expected distinct explanation and action.

#### T10 Add validation and limitations to the operator view
Owner: @gggnnnttt (proposed)  
Needs: T9  
Files: dashboard files, `README.md`, `docs/SOURCES.md`  
Done when: the screen identifies observed versus simulated inputs, timestamp/freshness, temperature evidence, route/slack evidence and “quality review required” as a hold for human review—not a claim that material is damaged or safe.
