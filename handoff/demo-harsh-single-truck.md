# Single-truck extreme-conditions demo

## State

Added the `harsh` scenario on `feat/demo-harsh-single-truck`. It presents one critical shipment with a simulated 40 °C exposure, a 45-minute route delay, and 20 minutes of production slack. The package reaches 15.0 °C in the initial replay frame, so quality review holds the shipment before logistics advice can authorize movement. The weighted prototype index is 97.5/100.

## Done

- Added the scenario to the Python replay, shared frontend scenario type, response validation, and selector.
- Added an on-screen German summary naming the three simulated conditions and quality-review precedence.
- Updated README, design notes, and decisions log.
- Manual scenario check returned one shipment, `quality_review`, 97.5/100, 45-minute delay, and 20-minute slack. Frontend production build passed.

## Next

- Review the new scenario in the running dashboard before presenting. All scenario readings and conditions are synthetic; the score is an illustrative priority index, not a product-quality probability.
