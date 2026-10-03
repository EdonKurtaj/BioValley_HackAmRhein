# Risk assessment model for refrigerated biopharma shipments

## Purpose and limits

This is a transparent prototype model for a critical, generic reagent/intermediate with a required handling band of **2–8 °C**. It estimates (1) thermal exposure of the shipment and (2) operational risk that logistics disruption makes the material late. These are different risks and should be displayed separately. The model supports planning and escalation; it does not decide product quality or replace a qualified cold-chain process.

The challenge does not name a product, packaging system, allowable excursion duration, stability curve, or approved route. Therefore, there is no scientifically defensible way to convert an excursion into a probability of degradation or a “safe time out of range.” Quality disposition must remain **review required** whenever the simulated/observed package sensor crosses 2–8 °C or its record is incomplete. WHO guidance supports transport monitoring and route profiling, but actual acceptance limits must come from the product owner/manufacturer and qualified packaging data. See [WHO TRS 961 Annex 9](https://www.who.int/publications/m/item/trs961-annex9) and [WHO TRS 992 Annex 5, Supplement 14](https://cdn.who.int/media/docs/default-source/medicines/norms-and-standards/guidelines/distribution/trs992-annex5.pdf).

## Inputs and what each can establish

| Input | Available fields in the saved sample | What it can tell us | What it cannot establish |
|---|---|---|---|
| MeteoSwiss Basel/Binningen current observations | Air temperature, 10-minute precipitation, radiation, sunshine, wind/gust, humidity/dew point, observation time | Ambient conditions near Basel at the station and time of observation; weather context for a simulated exposed transfer | Temperature inside the box or along the whole route; future conditions. Use observed measurements only, no forecast. |
| Basel-Stadt traffic dataset 100006 | Hourly counts by site, direction and lane; vehicle categories such as `pw`, `lief`, `lw`, `sattelzug`, `bus` | Whether observed counts at a selected corridor counter are unusual versus that same counter’s normal pattern | Congestion or vehicle travel time on its own. It is motorized-individual-traffic counting; category coverage varies by site. |
| Basel-Stadt Rhine dataset 100089 | Five-minute water level, level above sea level, discharge | Current local hydrology and rate/direction of change. Dataset is at Kleinbasel near the Birs inflow; its gauge convention is documented by Basel-Stadt. | A route closure unless paired with the official navigation threshold and the shipment’s actual Rhine leg. |
| Port of Switzerland current gauge page | Basel-Rheinhalle and harbour gauge, bridge clearance, Rhine water temperature; official flood marks | Operational river-navigation restrictions when the shipment’s ship leg uses the affected stretch | Truck route delay or product temperature. |
| Simulated shipment telemetry (later implementation) | Box sensor temperature/time; truck/ship location, route, status, ETA; loading/unloading and door-open intervals | Package thermal history and route-specific dwell/delay for the simulated shipment | Product quality disposition without product-specific stability and excursion rules. |

The saved requester samples are snapshots, not a representative historical baseline. Traffic currently returns only ten newest records, and the samples do not yet provide a route trace or package sensor history. Any historical comparison must first retrieve and retain a suitable time series.

## Calculation

The Python engine is in `src/risk_assessment/`. With no scenario argument, `PYTHONPATH=src python3 -m risk_assessment.cli` reads every risk input from Supabase and scores observed evidence only. Failed reads do not fall back to local snapshots. Local snapshot helpers remain available for offline callers and tests, but are not the CLI default. `--output-format json` returns the same structured score and evidence as the terminal output. Explicit CLI scenarios remain labelled simulations.

The web dashboard uses `python3 -m risk_assessment.server` and `GET /api/dashboard?mode=demo|live`. Live mode shows saved Supabase environmental measurements and regional event candidates with freshness; no live GPS/package feed exists yet. Demo mode supplies complete synthetic shipment inputs from `config/demo-transports.json` and reuses the same thermal, priority and decision functions. The resulting 100% coverage means all synthetic input groups are present, not that the model is calibrated. Authored route distances are displayed separately and never substitute for temperature or route evidence. A synthetic quality hold freezes the affected truck's movement while its package-temperature replay continues; the original ETA is shown as a planning value.

### 1. Package temperature: measured first, modelled only for scenarios

When the simulated embedded sensor is available, use its readings as the primary thermal input. Store timestamp, measured temperature, sensor accuracy/quality, and missing-data flags. Calculate and report, separately for hot and cold excursions:

```text
minutes_above_8 = sum(interval duration where T_box > 8 °C)
minutes_below_2 = sum(interval duration where T_box < 2 °C)
peak_above_8   = max(T_box - 8 °C, 0)
peak_below_2   = max(2 °C - T_box, 0)
hot_degree_hours  = Σ max(T_box_i - 8 °C, 0) × Δt_hours
cold_degree_hours = Σ max(2 °C - T_box_i, 0) × Δt_hours
```

Assume temperature changes linearly between adjacent readings only when the gap is at most the configured maximum (15 minutes by default); compute boundary-crossing minutes from the interpolated crossing time and degree-hours as the trapezoid/triangle area divided by 60. Do not interpolate across longer gaps; flag history incomplete and require review. Report sensor resolution/accuracy and gaps alongside the result. A reading exactly at 2 or 8 °C is within the stated band; an interval constant at either limit contributes zero excursion minutes and zero degree-hours. A transition from a limit to outside the band counts the interval except for the zero-duration boundary instant; show measurement uncertainty that reaches either boundary as “borderline / check sensor accuracy,” not as a proven excursion. Missing sensor accuracy is explicitly flagged for quality review.

Temperature-history assessment also requires an explicit `monitoring_started_at` and checks freshness at `evaluated_at` (current UTC time when omitted). At least two distinct readings are required; the first must cover the monitoring start, internal gaps must not exceed `max_gap`, and the last reading must be no more than `max_gap` old. The default 15-minute endpoint allowance is a demo monitoring tolerance, not a validated product limit. A missing start, single reading, missing beginning, or stale endpoint sets `incomplete_history`, requires quality review, and makes the thermal score unknown. Readings outside the requested interval and invalid/timezone-naive interval boundaries are rejected. Exposure is not extrapolated into the unmeasured tail. Simulations and historical replays explicitly assess their own interval endpoint rather than wall-clock time; this must not be used to label historical telemetry as current. Scenario JSON reports `incomplete_history`.

For a scenario before telemetry exists, use a first-order package thermal response as an *illustration*, not an excursion verdict. Choose explicit scenario values; do not randomly generate a value inside 2–8 °C and present it as a measurement. The demo uses repeatable 2, 5, and 7 °C starting cases:

```text
T_box(t + Δt) = T_air + (T_box(t) - T_air) × exp(-Δt / τ)
```

`τ` is the thermal time constant of the specific qualified package/load/airflow arrangement. It is unknown for this generic challenge. Expose it as a user-adjustable sensitivity parameter (fast, medium, slow response) and label the resulting temperature as **simulated**. Include sun/radiation and door-open handling only as scenario modifiers once the model can represent them; do not silently fold them into air temperature.

For constant ambient temperature, the estimated time to a limit gives the intuitive starting-temperature effect:

```text
Hot case, T_air > 8 °C: t_to_8 = τ × ln((T_air - T_start) / (T_air - 8 °C))
Cold case, T_air < 2 °C: t_to_2 = τ × ln((T_start - T_air) / (2 °C - T_air))
```

Thus a package starting at 7 °C reaches the upper boundary sooner than the same package starting at 2 °C during a hot exposure. In cold ambient conditions, a package starting at 2 °C has no lower-bound margin and reaches below 2 °C sooner than a warmer package. Compare a **2 °C / midpoint 5 °C / 7 °C** start in the demo. Do not claim that 2 °C is generally safer: it trades heat margin for freeze/cold margin.

### 2. Weather: link observations to the shipment’s place and time

Join the latest observed weather to a simulated transfer only when location/time are reasonably close. MeteoSwiss BAS is a regional outdoor station, not the loading dock or truck. Use:

- Air temperature for a hot/cold ambient scenario during a known exposed interval.
- Precipitation for wet-handling context only when a tracked stop/load is outdoors. Rain alone does not imply temperature damage; an enclosed, controlled box stays governed by its sensor.
- Global radiation/sunshine for potential solar loading if a package is outdoors/in an unshaded vehicle. Do not add a thermal penalty to an insulated/closed package without calibration.
- Wind/gust for exposed loading operations or disruption context if a supported relationship is defined.
- Humidity/dew point only for exposed packaging/condensation context, not as a cold-chain excursion score.

Missing values remain unknown, never zero. The current saved BAS sample has 17.1 °C, 0 mm precipitation over the latest 10 minutes, and 420 W/m² global radiation (observed at 11:20 local on 2026-10-03; fetched about 18 minutes later). This describes a dry current station observation; it says nothing about a shipment’s box temperature.

### 3. Traffic: anomaly signal, then ETA from tracking

Map only route-matched counter locations to the shipment’s simulated truck path. For each site/direction/lane (or a clearly defined site aggregation), build a baseline from historical counts for the same day-of-week and hour. Use median and median absolute deviation (MAD), or an empirical percentile, so a few incidents do not distort “normal”:

```text
traffic_anomaly = (observed_count - baseline_median) / max(1.4826 × MAD, minimum_scale)
```

The local detector labels a high-volume anomaly at robust z ≥ 3 as a configurable demo watch threshold. Keep total count and relevant heavy/commercial categories as separate context features; validate each site’s class coverage and metadata first. A high count is **unusual traffic volume**, not proof of congestion. With simulated GPS, use route progress/observed speed or simulated ETA to calculate delay against the planned ETA. Use traffic anomaly to explain/warn; use delay/remaining slack to decide urgency.

Basel-Stadt’s dataset describes motorized-individual-traffic counts and notes that full class data can be obtained in downloadable files; the current requester’s 10-row sample is not enough for a baseline. Collect several weeks (ideally seasonal coverage where feasible), retain site/direction/time, and handle the daylight-saving duplicated/missing hour as documented in the dataset.

### 4. Rhine: only affect a shipment with a ship leg

For a simulated ship leg, pair local river measurements with Port of Switzerland navigation information. Basel-Stadt dataset 100089 reports water level and discharge at Kleinbasel near the Birs inflow; the Port’s Basel-Rheinhalle gauge is the operational reference for the published high-water marks. Do not compare the gauges as if they were identical without an explicit conversion.

Port freshness uses the selected Basel-Rheinhalle reading’s `observed_at`, not `current_page_checked_at`. Page timestamps in `DD.MM.YYYY HH:MM` are interpreted in `Europe/Zurich` and converted to UTC; ISO timestamps must include an offset. Missing, invalid, future, ambiguous or nonexistent local measurement times remain unknown. Measurements older than the configurable `PORT_GAUGE_FRESHNESS_MINUTES` (30-minute demo default) are stale and excluded from current route scoring. Page-fetch age remains separately visible in JSON and the terminal; fetching a page again cannot refresh the measurement.

For high water, use the Port’s published status logic: 700 cm is a pre-alert; 790 cm closes large-vessel traffic between Basel/Mittlere Brücke and Birsfelden and certain small craft/ferry operations; 820 cm closes navigation between Rheinfelden and Kembs. Apply a restriction only if the shipment’s simulated ship leg intersects that stretch. These marks do not imply a truck delay.

Low water can constrain Rhine freight through reduced vessel loading/capacity and slower movement, but the present data and generic scenario do not define a universal low-water cutoff. For the demo, show the current level/discharge and classify low-water anomaly only against a longer season-matched local baseline, or against a vessel/operator draft threshold once available. Do not invent a hard threshold. A river restriction, rainfall-driven change, and resulting ship delay are one route consequence; do not add them as three independent risk penalties.

The current saved readings are around 479 cm at the Basel-Stadt gauge and 470 cm at Basel-Rheinhalle (separate gauges/timestamps), well below the Port’s 700 cm high-water pre-alert. This is a sample snapshot, not a general “normal” threshold and not evidence about low-water vessel capacity.

### 5. Logistics urgency and action

Calculate remaining production slack from shipment tracking and the required manufacturing time:

```text
slack_hours = time_until_material_is_needed - estimated_time_until_controlled_receipt
```

Use a demo configuration for the buffer threshold (for example, a few hours chosen for the storyboard); clearly label it as a scenario assumption until the factory supplies a real deadline and operating buffer. Base `Buffer`/`Expedite` primarily on route ETA/slack, and base `Reroute` on a known route restriction plus a feasible alternate route and ETA. Do not derive actual minutes of truck delay from counts alone. The local engine does not claim an ETA from present snapshots; caller-provided ETA, need-by time, and material need-by time are required for Buffer/Expedite; explicit route suitability and alternate ETA are required for Reroute.

Recommended decision order:

1. **Quality review / quarantine:** measured or simulated package sensor is outside 2–8 °C, or sensor history is missing/uncertain. This means hold for qualified review; the model does not conclude product is damaged.
2. **Reroute:** current route is closed/restricted or has a simulated disruption, and an alternate route is available with lower risk and acceptable ETA.
3. **Expedite:** thermal history remains in range but ETA consumes the configured production slack; prioritize the shipment/receiving operation.
4. **Buffer:** a disruption is plausible but there is enough slack; keep the material in controlled storage and avoid unnecessary handling.
5. **Normal:** no relevant route trigger, package reading within range, telemetry current, and sufficient slack.

### Observed open-data score (default CLI mode)

Observed CLI assessments read all environmental sources from Supabase. For Basel/Binningen (`BAS`) weather, they select the newest timestamped measurement batch in `observations` (`source_id = meteoswiss_basel_temperature`), so values from different observation times are not combined. Freshness is calculated from the source's `observed_at`, not the database fetch time or an archived age estimate. Missing, invalid or future weather and traffic observation times cannot enter the current score. Local snapshot helpers remain available to offline callers and tests, but failed CLI database reads do not fall back to archives.

Traffic context is limited to the newest 100 total-count observations. For each explicitly mapped counter, the CLI separately retrieves its newest total and the latest 52 older comparable weekday/hour observations for that same station, direction and lane. Limits apply after database filtering, so recent readings elsewhere do not displace route evidence. The minimum of five comparable observations still applies; insufficient history produces an unknown traffic signal. Dashboard reads do not request these baselines because the Live dashboard has no shipment route mappings.

The observed-only score uses four evidence groups: fresh weather during explicitly confirmed exposed handling, a fresh route-matched traffic anomaly with a comparable baseline, a fresh Port gauge matched to a supplied ship-leg segment, and caller-supplied ETA plus material need-by time. Its prototype maximum contributions are **weather context 40**, **production urgency 35**, **Rhine 15**, and **traffic 10** points. Package-temperature exposure is the highest-weight factor in the scenario score below; observed air temperature remains context and is not a package reading. The terminal summary reports evidence coverage as usable groups out of four; score-weight coverage is shown separately as weighted points out of 100. Stale/missing feeds and a Rhine gauge without a matching ship leg are listed as omitted with their reason. The total remains the sum of known weighted contributions.

Weather is a bounded handling-context proxy, not an estimate of box temperature. The demo triggers and ramps are explicit assumptions: hot ambient stress ramps from 30 to 40 °C, cold stress from 0 to −10 °C, ten-minute precipitation from 5 to 30 mm, and gust from 60 to 120 km/h. The weather severity is the maximum of those four subscores, so one storm is not counted repeatedly. Radiation, sunshine, humidity, dew point, mean wind and wind direction stay in the JSON output as context; they do not affect the score without a known exposed transfer or supported relationship. With exposed handling confirmed, a normal 18.4 °C observation, 0 mm precipitation and 7.2 km/h gust produce a weather severity of 0 and contribute **0 of the weather component's 40 points**.

Traffic contributes only when the observation is fresh and a same-counter/direction/lane/weekday/hour baseline is available. Its score is `clamp(max(robust_z, 0) / 3 × 100, 0, 100)`. A traffic volume anomaly is not a measured travel delay. Rhine contributes only for a fresh Port reading and a supplied matching ship leg: below the 700 cm pre-alert is 0, pre-alert scales from 25 to 100 until the segment restriction, and a restriction is 100. ETA urgency uses the same explicit buffer equation described below. These percentages and weights are configurable demo assumptions, not calibrated probabilities.

The terminal's **Data review** section lists exactly which values were used and which were omitted or treated as context only, with current observation ages and exclusion reasons. For example, when weather is fresh and exposed handling is confirmed but traffic is stale, no ship leg matches the Rhine gauge, and ETA/need-by are absent, evidence coverage is 1/4 groups (25%) while score-weight coverage is 40/100 points. Weather can contribute zero score points while still counting as one evidence group because valid measurements were considered. When weather also becomes stale, evidence coverage falls to 0/4.

### Scenario-only package and shipment score

For explicit simulations, display thermal exposure, route status, slack, and chosen action as distinct, explainable fields. This separate prototype score is calculated as:

```text
thermal_component = clamp((hot_degree_hours + cold_degree_hours) / 0.5 °C·h × 100, 0, 100)
route_component   = max(explicit route disturbance, route restriction, traffic anomaly component)
traffic_component = clamp(robust_traffic_z / 3 × 100, 0, 100)
urgency_component = clamp((buffer_hours - slack_hours) / buffer_hours × 100, 0, 100)

priority_score = 0.50 × thermal_component
               + 0.30 × urgency_component
               + 0.20 × route_component
```

The scenario weights and reference scales are centrally defined in `src/risk_assessment/config.py`; the terminal summary reads the same weights. Regression examples: three components at 50 severity contribute 25 thermal + 15 urgency + 10 route = 50 points. With only thermal severity 50 available, the bounds are 25–75 points because unknown urgency/route can contribute at most 50 more; evidence coverage is 1/3 groups (33.3%) and score-weight coverage is 50%.

Each component is on a 0–100 scale; the weights allocate up to 50 thermal, 30 urgency, and 20 route score points. Thermal exposure is scaled against a **demo reference of 0.5 °C·h**, traffic volume against the detector's **robust z = 3 watch threshold**, and urgency against the configurable production buffer (4 hours by default). These scales and weights are explicit prototype choices, not empirical product or factory risk parameters. Multiple simulated signals add to a higher score than any single signal's weighted contribution, as the challenge describes.

Both the scenario and observed outputs now use the same `decide_action` policy. **System Suggestion** is a presentation of the same action and reason, not a second score-threshold policy. Quality review has precedence and blocks onward delivery/production use. A route disturbance can suggest Reroute only with an available, explicitly suitable alternative whose arrival precedes the original ETA and meets the need-by time. A restricted route without such an alternative produces Monitor. ETA and need-by are required for other transport actions: slack below the configured buffer suggests Expedite; a shipment-related disruption with sufficient slack suggests Buffer. An unmatched traffic anomaly or weather without confirmed exposed handling cannot trigger an action. Normal requires package evidence, explicit route status, known handling context and sufficient slack; missing essential metadata produces Monitor. Observed-only mode can provide logistics advice but never Normal without package telemetry, and advice is not permission to release material. The score remains an illustrative explanatory index and does not authorize an action.

The scenario score interval uses incomplete evidence honestly. Known weighted contributions form its lower bound; each missing component can add up to its full weight for the upper bound. `coverage_percent` reports the share of thermal, route and urgency input groups with usable evidence; `score_weight_coverage_percent` separately reports how much of the score's total weight has evidence. Do not compare scores with substantially different evidence coverage as if they had equal certainty.

In scenario mode, traffic volume is not converted into travel minutes, and an anomaly plus route disruption combine by taking the larger route component. Outdoor weather can drive a package curve only in an explicitly requested simulation; it is never treated as measured box temperature. A quality review/hold is a separate deterministic rule triggered by simulated or measured package-temperature evidence and has no score threshold. Neither index is a probability of delay or damage, FMEA-derived RPN, product-quality verdict, or validated operational control. Calibration would require agreed factory criteria and outcome data. “Normal” means no modeled intervention trigger; it is not product release or proof of safety.

## Current local implementation boundaries

- The default CLI mode never simulates package temperature. Weather freshness is based on the actual station observation time, not merely the time the requester saved the file. Only an explicit scenario sends outdoor weather into the illustrative package-response model.
- Hourly traffic rows use a separate two-hour demo freshness window. This is a configurable prototype assumption pending confirmation of the dataset's update cadence.
- The saved traffic response is summarized, but the current ten-record sample has no multiweek, same-counter baseline. `traffic_volume_anomaly` returns unknown until like-for-like counts are supplied; an available anomaly is still not treated as congestion or delay.
- The Rhine helper uses the Basel-Rheinhalle level and Port high-water marks only when the caller names a matching ship-leg section. The Basel-Stadt gauge is shown separately; it is not converted. No low-water threshold is inferred.
- Route actions accept explicit evidence and ETA/slack inputs. Weather, rainfall, or river readings alone do not silently add score penalties.
- Product/customer records must not be exposed through anonymous Supabase reads. A separate Supabase access migration is provided to keep materials, lots, shipments and decisions service-side until a tenant-aware authenticated access design is agreed.

## Demo cases to prove the logic

1. **Hot loading delay:** 40 °C outside; package starts at 2 °C, 5 °C, or 7 °C; vary outdoor handling duration and package `τ`. Show predicted package curve as illustrative only. The 7 °C case approaches 8 °C first. Compare the same transfer with the box kept controlled/closed.
2. **Cold exposure:** ambient below 2 °C; compare start at 2 °C with 5 °C and 7 °C. Show the 2 °C case has the least lower-bound margin. Flag any sensor below 2 °C for quality review.
3. **Rain at unloading:** positive precipitation overlaps an outdoor tracked loading stop. Explain wet-handling/packaging concern separately; do not mark a thermal excursion unless the package sensor/model supports it.
4. **Traffic spike:** route-matched counter shows an unusual count for that weekday/hour and simulated ETA shows reduced slack. Recommend buffer or expedite based on slack; reroute only if an alternate route is represented.
5. **High Rhine:** ship leg intersects the affected section and Port status reaches a relevant mark. Recommend reroute/expedite only if feasible alternatives and schedule slack support it; otherwise report route disruption and supply risk.
6. **No evidence / stale feed:** missing weather, sensor gap, old telemetry, or a non-route river/traffic signal produces “unknown/monitor,” not a fabricated penalty.

## Evidence to collect next

Prioritize official/primary material over generic papers:

1. WHO TRS 961 Annex 9 (provided) and TRS 992 Annex 5 Supplements 13–15: route profiling, shipping-container qualification, and transport temperature-monitoring systems.
2. WHO TRS 1025 Annex 7, Good storage and distribution practices for medical products, for current distribution-quality framing.
3. Basel-Stadt metadata/codebooks for traffic dataset 100006 (class definitions and per-site coverage) and Rhine dataset 100089 (station/gauge definitions); Port of Switzerland navigation restrictions for Rhine operational rules.
4. MeteoSwiss official station/API field documentation and BAS station metadata for units, observation intervals and location.
5. Only if the model later claims product quality risk: manufacturer stability data, product-specific excursion policy, packaging qualification/thermal mapping, logger accuracy, and QA-approved handling SOP. University-access papers can inform thermal modelling or sensor methods, but cannot supply this missing product-specific disposition rule.

## Sources

- [WHO TRS 961 Annex 9: Model guidance for storage and transport](https://www.who.int/publications/m/item/trs961-annex9)
- [WHO TRS 992 Annex 5, Supplement 14: Transport route profiling qualification](https://cdn.who.int/media/docs/default-source/medicines/norms-and-standards/guidelines/distribution/trs992-annex5.pdf)
- [WHO TRS 961 Annex 9, Supplement 15: Transport monitoring systems](https://www.who.int/publications/m/item/Annex-9-n-trs-961)
- [WHO TRS 1025 Annex 7: Good storage and distribution practices](https://www.who.int/publications/m/item/trs-1025-annex-7)
- [Basel-Stadt traffic count dataset 100006](https://data.bs.ch/explore/dataset/100006/information/?flg=fr-ch)
- [Basel-Stadt Rhine level and discharge dataset 100089](https://data.bs.ch/explore/dataset/100089/table/?flg=de-ch&sort=timestamp)
- [Port of Switzerland water levels and navigation marks](https://port-of-switzerland.ch/hafenservice/pegel/)
- [MeteoSwiss automatic weather station field definitions](https://opendatadocs.meteoswiss.ch/a-data-groundbased/a1-automatic-weather-stations)

## OpenTransportData road evidence

The observed assessment now reads the newest of the combined collector and dedicated minute-watch OpenTransportData snapshots in addition to the existing feeds. It includes the regional event/counter candidate catalogue in JSON and reports candidate counts in the terminal. Selection by radius or place-name never establishes shipment relevance. All existing score weights and package-quality rules remain in force.

An optional `RoadCounterMatch` explicitly asserts that a detector's direction/lane is on the remaining shipment route, selects light or heavy vehicles, and supplies a comparable normal speed in km/h. The reference must come from documented operator knowledge or a suitable historical baseline; a speed limit is not a measured baseline. No reference is invented from the short archive. Only nonnegative finite class-specific speeds with positive class-specific flow and an observation age of 0–5 minutes are eligible. Heavy-vehicle speed is never replaced with car speed. Zero flow and missing/negative speeds remain unknown. The local signal is:

```text
speed_loss_percent = clamp(100 × (1 - measured_speed / supplied_normal_speed), 0, 100)
```

This is relative point-speed loss, not a congestion probability, travel-time multiplier, or delay estimate. One-minute sampling can be noisy; the five-minute freshness limit and 50% speed-loss action watch threshold are explicit demo policies. The ten-minute regular collector leaves periods without eligible minute-counter evidence; use its dedicated one-minute watch mode when demonstrating this component.

An optional `RoadEventMatch` asserts that an operator verified location, direction, vehicle applicability and effect (`disrupted` or `restricted`) for the exact `updated_at` version in the source. New/changed versions require review again. Event snapshots must be no more than 15 minutes old; source validity must be active or defined by a current validity interval. Revoked German/French/Italian/English messages, expired/future intervals and complex recurring schedules are excluded. Older snapshots without version/validity metadata stay visible but cannot trigger an event score; refresh with the updated collector. Message text is never used to invent delay minutes or determine truck restrictions automatically.

A verified current disruption uses the existing binary disturbance convention of severity 100. Combine selected eligible OpenTransportData signals with the maximum, then combine with the existing Basel traffic anomaly using the maximum, inside the existing ten-point traffic component. This prevents a message and speed reduction for the same incident being added twice. If some selected OpenTransportData evidence is unavailable, that subcomponent stays unknown unless a known signal already reaches its maximum of 100. Independent eligible Basel evidence can still contribute. Available evidence never proves that the whole route is clear.

A verified restriction feeds the existing alternate-route checks; speed loss at or above the watch threshold feeds the existing buffer/expedite policy. ETA and material need-by remain supplied shipment information. No route delay is added to ETA automatically, and public data never authorizes release of unmonitored material.

The observed output preserves `score` as the known weighted contribution and adds `minimum` and `maximum`: the upper bound adds the weights of unavailable components. With only traffic severity 50, the score is 5 and the missing-evidence range is 5–95. With no usable groups, score is null and the range is 0–100. These are bounds on missing component contributions, not statistical confidence intervals. Weather and Rhine retain their established applicability checks; radiation, humidity, additional river gauges and forecasts are context where no supported scoring relationship exists.

When combining explicitly selected count-baseline and OpenTransportData evidence by maximum, all selected sources must be available to report a complete traffic component. A known zero or partial speed loss cannot hide another selected source that is unknown. A known severity of 100 remains usable because missing evidence cannot increase that bounded maximum; exclusions remain visible.
