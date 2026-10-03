# Basel cold-chain risk prototype

> Built at [HackAmRhein 2026](https://hackamrhein.dev) with Codex. First time in this repository? The setup guide is [HACKAMRHEIN.md](HACKAMRHEIN.md).

This prototype explores how weather, traffic, and Rhine signals can inform cold-chain logistics planning for a generic refrigerated material. Package-temperature scenarios and observed local conditions are separate evidence.

## The problem

A Basel-area factory needs a critical refrigerated material on time while preserving its 2–8 °C handling conditions. This demo combines public environmental measurements with explicit shipment context to explain planning recommendations.

## How to run it

From the repository root, run the saved open-data observations only. This is the default and does not simulate package temperature, traffic, or ETA:

```sh
PYTHONPATH=src python3 -m risk_assessment.cli
```

The collector keeps local archives and also stores measurements in Supabase when the local `.env` is configured. See [collector setup](pythontest/README.md) and [database setup](supabase/README.md). The risk engine reads those same local archives; decision persistence is not implemented. Refresh observations before assessment (a successful fetch cannot make delayed source measurements current):

```sh
python3 pythontest/api_requester.py --once
```

By default, the CLI prints a readable summary with the risk score and data coverage. Add `--output-format json` for the full structured observations and score components. Run a package-temperature scenario explicitly with:

```sh
PYTHONPATH=src python3 -m risk_assessment.cli --scenario hot --start-c 7 --duration-minutes 60 --tau-minutes 90
```

Run all simulated decision cases beside the current observed-data assessment with:

```sh
PYTHONPATH=src python3 -m risk_assessment.cli --scenario all
```

The Normal, Buffer, Expedite, Reroute, and combined cases use explicit simulated route/ETA evidence. The observed-data score appears separately. No map or GPS trace is required to exercise the decision logic.

Choose `--scenario cold` for a cold exposure, or use `--scenario observed-weather` to simulate package response to the saved MeteoSwiss air temperature when the observation is no more than 30 minutes old. Stale or missing weather does not enter the observed-only score. Set `--ambient-c` to override the scenario ambient temperature. The package time constant is an illustrative input, not a qualified packaging property.

Run the calculation checks with:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

For shipment-specific observed planning, supply ETA and need-by timestamps with timezones, and explicit route evidence via `--route-status clear|disrupted|unknown`. Weather enters the score only with `--exposed-handling`; use `--controlled-handling` for a protected transfer. Without confirmed handling, weather stays context only. Map traffic counters to the route using repeated `--traffic-counter 'SITE|DIRECTION|LANE'` arguments, with exact identifiers from the source; a comparable historical baseline is still required. An alternative route requires `--alternate-route-available`, `--alternate-route-suitable`, and `--alternate-eta-at`; the alternate ETA must be earlier than the original and no later than material need-by. Suitability is explicitly supplied scenario/operator evidence, not inferred by a routing service.

Decision and System Suggestion share one policy. Missing essential shipment metadata produces Monitor; scores alone do not dispatch material. Observed-only logistics advice never authorizes product release.

Run the collector checks as well:

```sh
python3 -m unittest discover -s pythontest -p 'test_*.py'
```

## Data sources

See [docs/SOURCES.md](docs/SOURCES.md).

## Limits

Scenario package temperatures are simulated. Saved local weather is a regional observation, not a box sensor; the current ten-record traffic sample is not a route baseline; and river restrictions require a matching ship-leg section. The model has no product-specific stability rules and cannot decide whether goods are safe or damaged. It is a planning demo, not an operational or quality-release system.

## Team

GitHub usernames.
