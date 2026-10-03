"""Named prototype defaults; none are product-qualified acceptance limits."""

from datetime import timedelta

# The 2–8 °C band is the challenge's generic refrigerated example, not product data.
DEFAULT_MIN_TEMPERATURE_C = 2.0
DEFAULT_MAX_TEMPERATURE_C = 8.0

# Demo data-freshness window, not a source guarantee or operational SLA.
LOCAL_WEATHER_FRESHNESS_MINUTES = 30.0
PORT_GAUGE_FRESHNESS_MINUTES = 30.0  # Demo measurement-age limit, not a source SLA.
# Demo freshness allowance for hourly counts; confirm against source update cadence.
TRAFFIC_FRESHNESS_MINUTES = 120.0

# Conservative minimum for a demo robust baseline; production needs a validated history window.
MIN_TRAFFIC_BASELINE_SIZE = 5
TRAFFIC_MINIMUM_SCALE = 1.0
TRAFFIC_ANOMALY_THRESHOLD = 3.0  # Demo watch threshold; not a congestion/delay threshold.

# Open-data score weights sum to 100 points. They are demo priorities, not calibrated risk.
OPEN_WEATHER_WEIGHT = 40.0
OPEN_TRAFFIC_WEIGHT = 10.0
OPEN_RHINE_WEIGHT = 15.0
OPEN_URGENCY_WEIGHT = 35.0

# Scenario policy agreed in docs/decisions.md; illustrative, not calibrated risk.
THERMAL_WEIGHT = 0.50
URGENCY_WEIGHT = 0.30
ROUTE_WEIGHT = 0.20
THERMAL_REFERENCE_DEGREE_HOURS = 0.5
TRAFFIC_ANOMALY_REFERENCE_Z = TRAFFIC_ANOMALY_THRESHOLD

# Handling-context watch ranges; not product-quality limits or official weather warnings.
HOT_AMBIENT_ONSET_C = 30.0
HOT_AMBIENT_MAX_C = 40.0
COLD_AMBIENT_ONSET_C = 0.0
COLD_AMBIENT_MAX_C = -10.0
HEAVY_RAIN_ONSET_MM_10MIN = 5.0
HEAVY_RAIN_MAX_MM_10MIN = 30.0
STRONG_GUST_ONSET_KMH = 60.0
STRONG_GUST_MAX_KMH = 120.0

# Port of Switzerland Basel-Rheinhalle high-water marks (see docs/SOURCES.md).
RHINE_PRE_ALERT_CM = 700.0
RHINE_RESTRICTION_CM = {
    "basel_mittlere_bruecke_birsfelden": 790.0,
    "rheinfelden_kembs": 820.0,
}

# Illustrative UI scenario assumption only; replace with factory operating slack.
DEFAULT_BUFFER_HOURS = 4.0
DEFAULT_SENSOR_MAX_GAP = timedelta(minutes=15)

# Minute counters require a recent measurement, independent of the fetch time.
ROAD_COUNTER_FRESHNESS_MINUTES = 5.0
# Event snapshots are polled by the regular ten-minute collector.
ROAD_EVENT_FRESHNESS_MINUTES = 15.0
# Demo action watch threshold: 50% speed loss, not a calibrated congestion probability.
ROAD_SPEED_WATCH_SEVERITY = 50.0
