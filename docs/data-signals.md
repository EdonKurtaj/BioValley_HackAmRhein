# Current MeteoSwiss signals for the risk assessment

The requester reads the Basel/Binningen (`BAS`) row of the [MeteoSwiss all-stations current-observations CSV](https://data.geo.admin.ch/ch.meteoschweiz.messwerte-aktuell/VQHA80.csv). It saves every measurement column from that row, its observation time and a fetch-time age. A dash or blank means no reading and is saved as `null`, not zero. The current feed updates about every ten minutes; no weather forecast is used. [Field definitions](https://opendatadocs.meteoswiss.ch/a-data-groundbased/a1-automatic-weather-stations).

| Field | Measurement | Possible role in the demo |
|---|---|---|
| `tre200s0` | Air temperature, °C | Outdoor heat or cold during a transfer scenario. |
| `rre150z0` | Precipitation over the last ten minutes, mm | Wet or disrupted handling when goods are exposed; not a product-temperature reading. |
| `fu3010z0`, `fu3010z1` | Mean wind and peak gust, km/h | Loading-dock handling or route disruption context. |
| `gre000z0`, `sre000z0` | Global radiation, W/m², and sunshine duration, min | Possible solar exposure at an unprotected transfer point. |
| `ure200s0`, `tde200s0` | Relative humidity, %, and dew point, °C | Condensation or packaging context if the material is exposed. |
| `dkl010z0` | Mean wind direction, degrees | Context only unless a local handling rule needs it. |

The feed also includes pressure and tower-level fields; they remain in `measurements` even when this station has no value. A station observation is a regional weather signal, not a measurement at the truck, loading dock, container or material. It cannot establish a temperature excursion or product damage by itself.
