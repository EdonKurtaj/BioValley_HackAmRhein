"""Only strictly out-of-band temperature contributes excursion duration."""

import unittest
from datetime import datetime, timedelta, timezone

from risk_assessment.interfaces import TemperatureReading
from risk_assessment.thermal import analyze_temperature_series


class TemperatureBoundaryTests(unittest.TestCase):
    def analyze(self, first, second, accuracy=0):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(minutes=10)
        return analyze_temperature_series(
            [TemperatureReading(start, first, accuracy), TemperatureReading(end, second, accuracy)],
            monitoring_started_at=start, evaluated_at=end,
        )

    def test_constant_boundary_is_in_band_with_zero_duration_and_burden(self):
        for temperature in (2, 8):
            with self.subTest(temperature=temperature):
                result = self.analyze(temperature, temperature)
                self.assertEqual(result.minutes_above_max, 0)
                self.assertEqual(result.minutes_below_min, 0)
                self.assertEqual(result.hot_degree_hours, 0)
                self.assertEqual(result.cold_degree_hours, 0)
                self.assertFalse(result.quality_review_required)

    def test_boundary_to_in_band_and_back_has_no_excursion(self):
        for first, second in ((8, 7), (7, 8), (2, 3), (3, 2), (2, 8), (8, 2)):
            with self.subTest(first=first, second=second):
                result = self.analyze(first, second)
                self.assertEqual(result.minutes_above_max, 0)
                self.assertEqual(result.minutes_below_min, 0)
                self.assertFalse(result.quality_review_required)

    def test_boundary_to_outside_and_back_counts_positive_interval(self):
        for first, second, side in ((8, 9, "hot"), (9, 8, "hot"),
                                    (2, 1, "cold"), (1, 2, "cold")):
            with self.subTest(first=first, second=second):
                result = self.analyze(first, second)
                if side == "hot":
                    self.assertEqual(result.minutes_above_max, 10)
                    self.assertEqual(result.minutes_below_min, 0)
                    self.assertAlmostEqual(result.hot_degree_hours, 5 / 60)
                else:
                    self.assertEqual(result.minutes_below_min, 10)
                    self.assertEqual(result.minutes_above_max, 0)
                    self.assertAlmostEqual(result.cold_degree_hours, 5 / 60)
                self.assertTrue(result.quality_review_required)

    def test_crossing_still_counts_only_the_outside_fraction(self):
        for first, second, side in ((7, 9, "hot"), (9, 7, "hot"),
                                    (3, 1, "cold"), (1, 3, "cold")):
            with self.subTest(first=first, second=second):
                result = self.analyze(first, second)
                minutes = result.minutes_above_max if side == "hot" else result.minutes_below_min
                burden = result.hot_degree_hours if side == "hot" else result.cold_degree_hours
                self.assertEqual(minutes, 5)
                self.assertAlmostEqual(burden, 2.5 / 60)

    def test_boundary_uncertainty_still_requires_review_without_nominal_excursion(self):
        for temperature in (2, 8):
            with self.subTest(temperature=temperature):
                result = self.analyze(temperature, temperature, accuracy=0.1)
                self.assertEqual(result.minutes_above_max, 0)
                self.assertEqual(result.minutes_below_min, 0)
                self.assertEqual(result.borderline_readings, 2)
                self.assertTrue(result.quality_review_required)


if __name__ == "__main__":
    unittest.main()
