"""Package-temperature measurements and explicitly illustrative scenarios."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import exp, isfinite, log

from .config import DEFAULT_MAX_TEMPERATURE_C, DEFAULT_MIN_TEMPERATURE_C, DEFAULT_SENSOR_MAX_GAP
from .interfaces import ExposureMetrics, TemperatureReading


def _positive_linear_area(a: float, b: float, duration: float) -> float:
    """Integral of max(linear interpolation(a,b), 0) over duration."""
    if a >= 0 and b >= 0:
        return (a + b) * duration / 2
    if a <= 0 and b <= 0:
        return 0.0
    fraction = abs(a) / (abs(a) + abs(b))
    if a > 0:
        return a * duration * fraction / 2
    return b * duration * (1 - fraction) / 2


def _positive_duration(a: float, b: float, duration: float) -> float:
    """Duration for which linear interpolation between a and b is positive."""
    if a >= 0 and b >= 0:
        return duration
    if a <= 0 and b <= 0:
        return 0.0
    fraction = abs(a) / (abs(a) + abs(b))
    return duration * (1 - fraction if b > 0 else fraction)


def analyze_temperature_series(
    readings: list[TemperatureReading],
    minimum_c: float = DEFAULT_MIN_TEMPERATURE_C,
    maximum_c: float = DEFAULT_MAX_TEMPERATURE_C,
    max_gap: timedelta = DEFAULT_SENSOR_MAX_GAP,
) -> ExposureMetrics:
    """Compute boundary-crossing minutes and degree-hours by linear interpolation."""
    if not isfinite(minimum_c) or not isfinite(maximum_c) or minimum_c >= maximum_c:
        raise ValueError("temperature limits must be finite and minimum below maximum")
    if max_gap.total_seconds() <= 0:
        raise ValueError("max_gap must be positive")
    if not readings:
        return ExposureMetrics(0, 0, 0, 0, 0, 0, incomplete_history=True,
                               quality_review_required=True,
                               evidence=("No package-temperature readings are available.",))
    ordered = sorted(readings, key=lambda item: item.observed_at)
    for reading in ordered:
        if not isfinite(reading.temperature_c) or (reading.accuracy_c is not None
                and (not isfinite(reading.accuracy_c) or reading.accuracy_c < 0)):
            raise ValueError("temperatures must be finite and known accuracy cannot be negative")
        if reading.observed_at.tzinfo is None or reading.observed_at.utcoffset() is None:
            raise ValueError("reading timestamps must include a timezone")
    if any(a.observed_at == b.observed_at for a, b in zip(ordered, ordered[1:])):
        raise ValueError("reading timestamps must be unique")

    hot_minutes = cold_minutes = hot_dh = cold_dh = peak_hot = peak_cold = 0.0
    borderline = 0
    accuracy_unknown = False
    incomplete = False
    out_of_range = False
    for reading in ordered:
        if reading.accuracy_c is None:
            accuracy_unknown = True
        elif reading.accuracy_c > 0:
            low = reading.temperature_c - reading.accuracy_c
            high = reading.temperature_c + reading.accuracy_c
            if low <= minimum_c <= high or low <= maximum_c <= high:
                borderline += 1
        if reading.temperature_c < minimum_c or reading.temperature_c > maximum_c:
            out_of_range = True
        peak_hot = max(peak_hot, reading.temperature_c - maximum_c, 0.0)
        peak_cold = max(peak_cold, minimum_c - reading.temperature_c, 0.0)

    for first, second in zip(ordered, ordered[1:]):
        elapsed = (second.observed_at - first.observed_at).total_seconds()
        if elapsed <= 0:
            raise ValueError("reading timestamps must be strictly increasing")
        if elapsed > max_gap.total_seconds():
            incomplete = True
            continue  # Do not invent an exposure curve across an unobserved gap.
        minutes = elapsed / 60
        x0, x1 = first.temperature_c, second.temperature_c
        hot_minutes += _positive_duration(x0 - maximum_c, x1 - maximum_c, minutes)
        cold_minutes += _positive_duration(minimum_c - x0, minimum_c - x1, minutes)
        hot_dh += _positive_linear_area(x0 - maximum_c, x1 - maximum_c, minutes) / 60
        cold_dh += _positive_linear_area(minimum_c - x0, minimum_c - x1, minutes) / 60
    review = out_of_range or borderline > 0 or incomplete or accuracy_unknown
    evidence = []
    if out_of_range:
        evidence.append("A nominal package reading is outside the configured temperature band.")
    if borderline:
        evidence.append("Measurement uncertainty touches a temperature limit; verify sensor accuracy.")
    if accuracy_unknown:
        evidence.append("Sensor accuracy is not recorded; quality review is required.")
    if incomplete:
        evidence.append("One or more sensor gaps exceed the configured maximum gap; exposure is incomplete.")
    return ExposureMetrics(hot_minutes, cold_minutes, peak_hot, peak_cold,
                           hot_dh, cold_dh, borderline, incomplete, review, tuple(evidence), accuracy_unknown)


def simulate_package_temperature(
    start_c: float,
    ambient_c: float,
    duration: timedelta,
    time_constant: timedelta,
    step: timedelta = timedelta(minutes=1),
) -> list[TemperatureReading]:
    """Generate deterministic first-order package response; this is not sensor data."""
    values = (start_c, ambient_c, duration.total_seconds(), time_constant.total_seconds(), step.total_seconds())
    if not all(isfinite(value) for value in values):
        raise ValueError("scenario inputs must be finite")
    if duration.total_seconds() <= 0 or time_constant.total_seconds() <= 0 or step.total_seconds() <= 0:
        raise ValueError("duration, time constant, and step must be positive")
    origin = datetime.now().astimezone().replace(microsecond=0)
    count = int(duration.total_seconds() // step.total_seconds())
    samples = [0, *[int(i * step.total_seconds()) for i in range(1, count + 1)]]
    if samples[-1] < duration.total_seconds():
        samples.append(int(duration.total_seconds()))
    return [
        TemperatureReading(origin + timedelta(seconds=seconds),
                           ambient_c + (start_c - ambient_c) * exp(-seconds / time_constant.total_seconds()), 0.0)
        for seconds in samples
    ]


def time_to_temperature_limit(start_c: float, ambient_c: float, limit_c: float, time_constant: timedelta) -> float | None:
    """Return minutes to a boundary under constant ambient; None if not approached."""
    tau = time_constant.total_seconds()
    if tau <= 0 or not all(isfinite(x) for x in (start_c, ambient_c, limit_c, tau)):
        raise ValueError("temperatures must be finite and time constant positive")
    if start_c == limit_c:
        return 0.0
    ratio = (limit_c - ambient_c) / (start_c - ambient_c) if ambient_c != start_c else -1
    if not 0 < ratio < 1:
        return None
    return -tau * log(ratio) / 60
