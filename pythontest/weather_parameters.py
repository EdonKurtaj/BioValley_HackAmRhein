"""Requested VQHA80 weather parameters; verified against MeteoSwiss metadata.

Source: https://opendatadocs.meteoswiss.ch/a-data-groundbased/a1-automatic-weather-stations
Units: https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/ogd-smn_meta_parameters.csv
"""

WEATHER_PARAMETERS = {
    "tre200s0": {"name_en": "Air temperature at 2 m", "name_de": "Lufttemperatur in 2 m Höhe",
                 "unit": "°C", "aggregation": "instantaneous"},
    "rre150z0": {"name_en": "Precipitation", "name_de": "Niederschlag",
                 "unit": "mm", "aggregation": "sum", "interval_minutes": 10},
    "gre000z0": {"name_en": "Global radiation", "name_de": "Globalstrahlung",
                 "unit": "W/m²", "aggregation": "mean", "interval_minutes": 10},
    "sre000z0": {"name_en": "Sunshine duration", "name_de": "Sonnenscheindauer",
                 "unit": "min", "aggregation": "sum", "interval_minutes": 10},
    "fu3010z0": {"name_en": "Wind speed", "name_de": "Windgeschwindigkeit",
                 "unit": "km/h", "aggregation": "mean", "interval_minutes": 10},
    "fu3010z1": {"name_en": "Peak wind gust", "name_de": "Maximale Windböe",
                 "unit": "km/h", "aggregation": "maximum", "interval_minutes": 10},
    "dkl010z0": {"name_en": "Wind direction", "name_de": "Windrichtung",
                 "unit": "°", "aggregation": "mean", "interval_minutes": 10},
    "ure200s0": {"name_en": "Relative humidity at 2 m", "name_de": "Relative Luftfeuchtigkeit in 2 m Höhe",
                 "unit": "%", "aggregation": "instantaneous"},
    "tde200s0": {"name_en": "Dew point at 2 m", "name_de": "Taupunkt in 2 m Höhe",
                 "unit": "°C", "aggregation": "instantaneous"},
}
