# Sources

## OpenTransportData road traffic (new collector)

- **Traffic Situations (road traffic):** live messages for incidents, congestion, closures, work zones, restrictions, validity, direction, descriptions and event type. The collector retains Basel-region locality matches and records with coordinates within 55 km of Basel, including inbound/outbound approach corridors; some text matches can refer to farther sections of a route to Basel. The feed itself provides the current active/update messages, not historical data.
- **Traffic counters:** the static Measurement Site Table supplies site coordinates, detector/lane identity and available measurement types. The collector requests dynamic readings from counter sites within 55 km of Basel and records current light/heavy vehicle counts and average speeds with observation timestamps. The large site table is cached locally for up to seven days; readings can be archived once per new measurement minute.
- The regular `python3 pythontest/api_requester.py` cycle fetches this combined source and normalizes numeric counter flow/speed observations for Supabase. Generated combined snapshots and counter history are stored locally beneath the collector's data directory and are not checked into the repository. Run `python3 pythontest/opentransportdata.py --watch` separately for one-minute polling and faster baseline collection. API keys are read from local `.env` variables `OTD_TRAFFIC_SITUATIONS_API_KEY` and `OTD_TRAFFIC_COUNTERS_API_KEY`; never put actual key values in this document or `.env.example`.
- The 55 km radius and message place-name filter intentionally collect approach-route alternatives, not only Basel-Stadt canton records. Text-only locations need route verification. The collected events/counter values are live evidence, not a shipment ETA; route matching and like-for-like archived history are still needed before using traffic values as a numeric anomaly or expedite trigger.
- Primary documentation: [Traffic Situations](https://opentransportdata.swiss/en/cookbook/road-traffic-cookbook/traffic-situations/), [real-time road traffic counters](https://opentransportdata.swiss/en/cookbook/road-traffic-cookbook/rt-road-traffic-counters/), [API key access](https://opentransportdata.swiss/de/cookbook/development-miscellaneous-cookbook/howto-access-apis/). FEDRO terms apply.

Every dataset, API, notable library and AI tool used, with licence. Feeds the sources slide on Sunday.

| What | Source / URL | Licence or permission | Used for |
|---|---|---|---|
| Codex (OpenAI) | chatgpt.com/codex | Tool, AI-assisted development | Coding assistant |
| OpenStreetMap | https://www.openstreetmap.org/copyright | ODbL map data; standard tile usage policy at https://operations.osmfoundation.org/policies/tiles/ | Basel basemap, visible attribution; no bulk downloading |
| MapLibre GL JS | https://maplibre.org/maplibre-gl-js/docs/ | BSD-3-Clause | Interactive Basel map |
| React and Vite | https://react.dev and https://vite.dev | MIT | Standalone frontend and development tools |
| Illustrative map locations | Authored for this prototype | Project-authored example data | Orientation only; no observed measurements |
| Demo truck routes and shipment telemetry | config/demo-transports.json; authored for this prototype | Project-authored synthetic data | Reproducible truck replay, authored route polylines, timing and simulated temperatures; no real customers or GPS traces; not navigation-qualified |
| Basel motor traffic counts (dataset 100006) | https://data.bs.ch/explore/dataset/100006/ | Basel-Stadt Open Government Data terms; CC0-style open reuse | Traffic observations for logistics disruption |
| Basel Rhine water level and discharge (dataset 100089) | https://data.bs.ch/explore/dataset/100089/ | Basel-Stadt Open Government Data terms; CC0-style open reuse | Rhine corridor risk observations |
| MeteoSwiss current observations | https://data.geo.admin.ch/ch.meteoschweiz.messwerte-aktuell/VQHA80.csv | Federal open data; attribution: Source: MeteoSwiss | Basel/Binningen temperature, precipitation, radiation, sunshine, wind/gust/direction, humidity and dew point |
| MeteoSwiss parameter metadata | https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/ogd-smn_meta_parameters.csv and https://opendatadocs.meteoswiss.ch/a-data-groundbased/a1-automatic-weather-stations | Federal open data; attribution: Source: MeteoSwiss | Verified weather parameter identifiers, units and aggregation intervals |
| OpenTransportData road traffic situations and counters | https://opentransportdata.swiss/en/cookbook/road-traffic-cookbook/rt-road-traffic-counters/ | FEDRO terms apply | Basel-region traffic events and live vehicle speed/flow observations |
| Port of Switzerland gauge pages | https://port-of-switzerland.ch/hafenservice/pegel/ | Website terms apply | Current and forecast Rhine navigation conditions |
| WHO TRS 961 Annex 9 | https://www.who.int/publications/m/item/trs961-annex9 | © World Health Organization; permission terms apply | Background on cold-chain storage, transport monitoring, stock tracking and suspect-product quarantine |
| WHO TRS 992 Annex 5, Supplement 14 | https://cdn.who.int/media/docs/default-source/medicines/norms-and-standards/guidelines/distribution/trs992-annex5.pdf | © World Health Organization; permission terms apply | Transport route profiling and qualification |
| WHO TRS 961 Annex 9, Supplement 15 | https://www.who.int/publications/m/item/Annex-9-n-trs-961 | © World Health Organization; permission terms apply | Temperature and humidity monitoring systems for transport operations |
| WHO TRS 1025 Annex 7 | https://www.who.int/publications/m/item/trs-1025-annex-7 | © World Health Organization; permission terms apply | Current good storage and distribution practice background |
