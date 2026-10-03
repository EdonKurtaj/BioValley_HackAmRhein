# Data request notes

## Rhine water level and discharge — dataset 100089

The requester uses `RHINE_RECORD_LIMIT = 48` in this source's `params`, with `offset=0` and `order_by=-timestamp`. URL parameters are encoded when constructing the request; the archive records the full requested URL.

The [official Explore API documentation](https://help.opendatasoft.com/apis/ods-explore-v2/) states that the maximum `limit` is 100. Live boundary checks against the [Basel-Stadt records endpoint](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089/records/) on 2026-10-03 confirmed:

| Requested limit | HTTP status | Response |
| --- | --- | --- |
| 200 | 400 | InvalidRESTParameterError; limit must be between -1 and 100 |
| 100 | 200 | 100 records returned |
| 101 | 400 | InvalidRESTParameterError; limit must be between -1 and 100 |
| 48 | 200 | 48 records returned in the requester's live `--once` run |

All checks used `lang=en`, `offset=0`, and `order_by=-timestamp`. Example [rejected limit=200 request](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089/records/?lang=en&limit=200&offset=0&order_by=-timestamp) and [configured limit=48 request](https://data.bs.ch/api/explore/v2.1/catalog/datasets/100089/records/?lang=en&limit=48&offset=0&order_by=-timestamp).

The saved 48 rows span 2026-10-03 05:15 to 09:10 UTC. At a five-minute cadence, 48 samples cover approximately four hours; the interval between the oldest and newest sample is 47 × 5 minutes = 3 hours 55 minutes. Missing observations can change that span; use the actual timestamps when calculating rates.

The earlier live acceptance check confirmed 48 results in the collector's local dataset-100089 snapshot. That generated archive is not checked into the repository; current assessment reads saved Supabase observations.

## Traffic — dataset 100006

The traffic request remains unchanged at `limit=10`, ordered by `-datetimefrom`. The live run returned 10 records. A counting-station filter is outside this change.

## MeteoSwiss current measurements

The requester continues to read the current-values CSV directly. The old STAC station-fetch function, parameter-metadata loader, and metadata URL constant were removed after a repository search found no external callers. `parse_csv_value`, `csv`, `io`, `ZoneInfo`, and `re` remain in use.

The collector now retains nine requested weather metrics for BAS: air temperature, precipitation, global radiation, sunshine duration, mean wind speed, peak gust, wind direction, relative humidity, and dew point. [weather_parameters.py](../pythontest/weather_parameters.py) is the home for parameter identifiers, units, and aggregation windows, verified against the official [MeteoSwiss documentation](https://opendatadocs.meteoswiss.ch/a-data-groundbased/a1-automatic-weather-stations) and parameter metadata CSV.

All available metrics use the source's observation timestamp, not the request time. Missing or non-finite values are retained as null in the local payload and listed under `missing_measurements`; they create no Supabase observations. Valid zero values remain measurements. A partially available weather row remains usable, including when temperature is missing; a row with no valid requested measurements is marked failed. Observation dimensions record aggregation and, where applicable, the ten-minute interval. The existing source ID is retained to preserve the temperature series.

Live validation on 2026-10-03 confirmed all nine metrics in the source response and in Supabase for the 10:00 UTC observation (12:00 Europe/Zurich). No schema change was needed. Restart an already running collector after updating the code; a process that imported the older code continues collecting only temperature until restarted.

The live `--once` run completed with HTTP 200 for all five sources and successful port transformation. MeteoSwiss still prints temperature, the observation time in Europe/Zurich, and measurement age in the same format; an offline test checks the exact status line with a fixed clock.

## Port number formats

On 2026-10-03, searching the saved HTML pages for digit-apostrophe-digit patterns found no straight or curly thousands separators. The previous parser did not handle those formats reliably, so support was added as a preventive fix.

`parse_swiss_number` accepts straight and curly apostrophes, narrow/thin/non-breaking grouping spaces, comma decimals, decimal points, and signed values. HTML extraction normalizes grouping whitespace to regular spaces, which are also supported. Measurement parsing separates an optional `ca.` prefix and the unit before converting the number.

Integral numeric values return `int`; fractional values return `float`. Forecast fields retain their existing float representation for output compatibility. Transformation of the saved example pages was compared before and after the change: the serialized output is identical, excluding the generated `updated_at` timestamp.
