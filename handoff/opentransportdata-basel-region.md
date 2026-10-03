# OpenTransportData Basel-region collection

## State

Implemented on `feat/local-risk-assessment`; changes are uncommitted. Live API requests now succeed with both configured OpenTransportData tokens. The feed is also registered in the regular API requester.

## Done

- Added `pythontest/opentransportdata.py` to fetch Traffic Situations and the traffic-counter master/dynamic feeds over HTTPS/SOAP, decompress gzip responses, parse DATEX II XML, and retain Basel-region candidate events plus nearby counters.
- Expanded collection to a 55 km radius around Basel and place-name matches for wider inbound/outbound corridors. The output is a route-context candidate set, not a route match.
- Cached counter site metadata for seven days and added optional `--watch` polling (60-second minimum) with a local per-minute counter history.
- Added the combined Basel-region feed to `api_requester.py`; its normal cycle now saves the traffic payload, preserves the dedicated counter history, and normalizes numeric speed/flow readings for the existing Supabase ingestion path. Situation messages remain available in the raw payload.
- Latest live pull (2026-10-03): 175 traffic situation records; 329 counter sites; 328 current readings; 328 readings written to the local history.
- Verified Python compilation, sample XML parser filtering, live feed requests and `git diff --check`.

## Next

- Run `python3 pythontest/api_requester.py --once` to collect it through the regular source cycle, or keep a `--watch` run going to build history; then compare same-site, same-hour speeds/flows before scoring traffic anomalies.
- Match events and counters to actual shipment/alternate-route corridors before using them to recommend an expedite or reroute. The 55 km and place-name filter deliberately includes extra approach-route traffic.
- Live OpenTransportData is archived separately; the existing observed risk score does not yet consume this new feed.
