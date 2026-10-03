# Risk assessment workstream plan

Scope: a demonstrable decision aid for a **critical refrigerated biopharma reagent or intermediate** used in Basel-area manufacturing, as specified in `docs/challenge.md`. It requires 2-8 °C handling and timely availability for production; no particular product is named. Packaging, route and transfer times remain scenario assumptions until the team chooses them. This plan covers the risk assessment workstream; the overall app design still needs `docs/design.md` and team ownership can be reassigned.

**Decision to demonstrate:** show (1) a disruption level for replenishment and (2) whether this shipment's temperature handling may need quality review. Do not collapse these into an unexplained pharmaceutical "safety score." Public weather, river and traffic data are hazard indicators; they are not measurements of the material's temperature or proof of degradation. A release or rejection decision requires product-specific stability limits and qualified-person review.

Task status belongs in `handoff/<task>.md`. Owners are proposed because no `TEAM.md` identifies other contributors yet. Each task should fit one focused chat; parallel tasks touch separate files.

## M1 Evidence and scenario: the team can explain what each signal means

### Chunk A - parallel, start now

#### T1 Define the shipment and the demo decision
Owner: @gggnnnttt (proposed)
Needs: nothing
Files: `docs/design.md`
Done when: one page states the challenge's critical refrigerated biopharma reagent or intermediate, its starting temperature at transfer, route/mode, packaging, transfer point, intended production time, what the operator sees, and who decides after an excursion.
Notes: Record assumptions prominently. The user should be able to compare a starting temperature of 2 °C with 7 °C in the same hot-weather scenario. Ask whether the Rhine is actually on this material's supply route. A road-only delivery has no direct river-level dependency.

#### T2 Build an evidence table for each risk claim
Owner: @gggnnnttt (proposed)
Needs: nothing
Files: `docs/risk-evidence.md`, `docs/SOURCES.md`
Done when: each proposed rule has a source, a physical or operational mechanism, its required input, and a statement of what it cannot prove. Separate WHO/ICH process guidance from product-specific stability evidence.
Notes: Start with WHO TRS 961 Annex 9 sections 3.3, 6.2-6.3, 6.5, 6.8, 8.2 and 9.1; WHO Supplements 13-15; ICH Q9(R1); and ICH Q5C if the chosen material is a biological product. Seek manufacturer stability/excursion limits only after T1 names a product. University papers may help explain heat transfer or a specific molecule, but generic papers cannot set release limits for another product.

#### T3 Audit the five source feeds and their timing
Owner: @gggnnnttt (proposed)
Needs: nothing
Files: `docs/data-signals.md`
Done when: a table lists the field, unit, station/location, observation timestamp, update lag, route relevance, and supported inference for each source; it explicitly marks missing precipitation, starting material temperature, shipment logger trace, route/ETA, packaging, handling duration, inventory and product stability data.
Notes: `port_pegel_clean` is a transformation of the two Port pages, not a sixth independent source. Current `history.jsonl` files hold one fetch each; the traffic API response is only 10 records, so no historical baseline is available locally yet. Traffic counts must not be called measured congestion or delay.

## M2 Transparent decision logic: every recommendation has a traceable reason

### Chunk B - parallel after M1 evidence is ready

#### T4 Create realistic test scenarios
Owner: @gggnnnttt (proposed)
Needs: T1, T2, T3
Files: `docs/risk-scenarios.md`
Done when: the team can read at least six scenarios and agree on the expected action: routine shipment; 40 °C air with short protected transfer starting at 2 °C; the same transfer starting at 7 °C; 40 °C air with delayed/unprotected transfer; route disruption without temperature evidence; and a documented temperature excursion or missing logger record.
Notes: Include a cold-weather case near 2 °C as well. Include both high- and low-water examples only if the route uses Rhine freight. Add rain only as a clearly labelled hypothetical until a precipitation feed is added. Each scenario states what is measured, assumed and unknown.

#### T5 Define the thermal-exposure calculation
Owner: @gggnnnttt (proposed)
Needs: T1, T2, T3
Files: `docs/thermal-model.md`
Done when: the same 40 °C exposure produces a shorter estimated time to reach 8 °C from a 7 °C start than from a 2 °C start, and every result displays its assumptions and uncertainty. The model also checks the lower 2 °C boundary in cold scenarios.
Notes: Prefer actual material/container logger data if available. Otherwise use a simple thermal-response model with an explicit package response parameter; derive that parameter from a small instrumented container test or qualified package data. If it is guessed, label the temperatures as illustrative and show a range for plausible packaging. WHO Supplement 14's degree-hours describe exposure and container qualification, not product damage. Outdoor station temperature is only a scenario proxy for the air at the loading dock.

### Chunk C - in order

#### T6 Specify the risk and action rules
Owner: @gggnnnttt (proposed)
Needs: T4, T5
Files: `docs/risk-rules.md`
Done when: a reviewer can apply the written decision table by hand to the scenarios and get the same disruption level, temperature-exposure assessment and action, including an "insufficient evidence" outcome.
Notes: Distinguish `supply delay` from `possible temperature exposure`. Use official Rhine high-water navigation thresholds only for a relevant water route; obtain a route-specific low-water threshold before using one. Use a local time-of-day/site traffic baseline or an ETA feed before treating counts as delay. Estimated crossing of 8 °C from a hypothetical thermal model is a preventive alert, not proof of an actual excursion. A measured excursion, damaged package, or missing required record triggers hold under controlled conditions and quality review; it does not prove product loss. Keep risk thresholds as explicit demo assumptions until validated.

#### T7 Check rules against scenarios and domain review
Owner: @gggnnnttt (proposed)
Needs: T6
Files: `docs/risk-validation.md`
Done when: all scenarios show expected versus actual assessment, each mismatch is resolved or documented, and someone familiar with pharmaceutical handling has checked the terminology and action boundaries.
Notes: A simple cross-check against WHO and the source evidence is sufficient for the demo. Record uncertainties rather than tuning arbitrary weights to produce a desired colour.

## M3 Demo handoff: the model can be built and explained honestly

### Chunk D - in order

#### T8 Hand off a build-ready risk model
Owner: @gggnnnttt (proposed)
Needs: T7
Files: `docs/risk-model-handoff.md`
Done when: the builder has a compact input/output table, worked 40 °C examples starting at 2 °C and 7 °C, action explanations, source links, and a clear list of simulated inputs and limits for the demo.
Notes: Keep the demo working from saved examples if live APIs fail. Implementation and user interface tasks can then be added to the wider project plan after `docs/design.md` is agreed.

## Current evidence boundary

- **Temperature:** the saved MeteoSwiss record measures outdoor air at Basel/Binningen, not truck, container or product temperature. The 40 °C case is a scenario, not the latest observation.
- **Traffic:** dataset 100006 gives hourly counts by site, lane and vehicle class. The saved response's newest row is from 30 September 2026, while the other feeds were fetched on 3 October 2026. It does not give actual travel time.
- **Rhine:** dataset 100089 and Port pages provide water level/discharge and a forecast. The Port publishes high-water navigation marks at Basel-Rheinhalle (700 cm pre-alert, 790/820 cm closures for specified sections). These support route disruption rules only for Rhine-linked shipments. Low water can reduce loading capacity, but a usable threshold depends on vessel, section and route.
- **Rain:** no precipitation value is in the saved requester output. Rain may matter to exposed handling or road operations, but no rain rule can be calculated from these files.
- **Shipment:** no product-specific stability profile, logger trace, packaging qualification, dock transfer time, actual ETA or inventory slack is present. The model can recommend preventive action and quality review, but cannot determine actual product damage or release.
