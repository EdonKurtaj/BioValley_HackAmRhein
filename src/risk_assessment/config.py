"""Named prototype defaults; none are product-qualified acceptance limits."""

from datetime import timedelta

# The 2–8 °C band is the challenge's generic refrigerated example, not product data.
DEFAULT_MIN_TEMPERATURE_C = 2.0
DEFAULT_MAX_TEMPERATURE_C = 8.0

# Demo data-freshness window, not a source guarantee or operational SLA.
LOCAL_WEATHER_FRESHNESS_MINUTES = 30.0
# Demo freshness allowance for hourly counts; confirm against source update cadence.
TRAFFIC_FRESHNESS_MINUTES = 120.0

# Conservative minimum for a demo robust baseline; production needs a validated history window.
MIN_TRAFFIC_BASELINE_SIZE = 5
TRAFFIC_MINIMUM_SCALE = 1.0
TRAFFIC_ANOMALY_THRESHOLD = 3.0  # Demo watch threshold; not a congestion/delay threshold.

# Illustrative UI scenario assumption only; replace with factory operating slack.
DEFAULT_BUFFER_HOURS = 4.0
DEFAULT_SENSOR_MAX_GAP = timedelta(minutes=15)
