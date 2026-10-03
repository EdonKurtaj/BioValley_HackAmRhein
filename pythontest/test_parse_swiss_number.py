"""Swiss number formats across port measurements and forecasts."""

import unittest

from transform_port_pegel import number_and_unit, page_tables, parse_current, parse_forecast, parse_swiss_number


class SwissNumberTests(unittest.TestCase):
    def test_numeric_formats_and_types(self):
        cases = (
            ("2'800", 2800, int),
            ("2’800", 2800, int),
            ("2\u202f800", 2800, int),
            ("2\u00a0800", 2800, int),
            ("2\u2009800", 2800, int),
            ("1,5", 1.5, float),
            ("744.982", 744.982, float),
            ("-0,3", -0.3, float),
            ("2'800,5", 2800.5, float),
        )
        for text, expected, expected_type in cases:
            with self.subTest(text=text):
                value = parse_swiss_number(text)
                self.assertEqual(value, expected)
                self.assertIs(type(value), expected_type)

    def test_approximation_and_unit_are_separate_from_number(self):
        self.assertEqual(number_and_unit("ca. 2'800 m³/s"), (2800, "m³/s"))
        self.assertEqual(number_and_unit("-0,3 m"), (-0.3, "m"))

    def test_current_readings_and_thresholds_handle_swiss_grouping(self):
        tables = [
            [["Gewässer/See", "Aktueller Wert", "Zeit"], ["Basel", "2’800 cm", "08:00"]],
            [["Hochwassermarke", "Pegel", "Abflussmenge Basel-Rheinhalle"],
             ["I", "744.982 m", "ca. 2'800 m³/s"]],
        ]
        readings, thresholds = parse_current(tables)
        self.assertEqual(readings[0]["value"], 2800)
        self.assertIs(type(readings[0]["value"]), int)
        self.assertEqual(thresholds[0]["discharge_approx"], 2800)
        self.assertIs(type(thresholds[0]["discharge_approx"]), int)
        self.assertEqual(thresholds[0]["discharge_unit"], "m³/s")

    def test_forecast_handles_swiss_grouping(self):
        tables = [[["Datum - Zeit", "Pegel", "Abfluss"], ["08:00", "744,982", "2'800"]]]
        forecast = parse_forecast(tables, "")
        self.assertEqual(forecast["rows"][0]["water_level_m_above_sea_level"], 744.982)
        self.assertEqual(forecast["rows"][0]["discharge_m3_per_second"], 2800.0)
        self.assertIs(type(forecast["rows"][0]["discharge_m3_per_second"]), float)

    def test_html_whitespace_normalization_preserves_grouped_number(self):
        tables, _ = page_tables(
            "<table><tr><th>Gewässer/See</th><th>Aktueller Wert</th><th>Zeit</th></tr>"
            "<tr><td>Basel</td><td>2&#8239;800 m³/s</td><td>08:00</td></tr></table>"
        )
        readings, _ = parse_current(tables)
        self.assertEqual(readings[0]["value"], 2800)
        self.assertEqual(readings[0]["unit"], "m³/s")


if __name__ == "__main__":
    unittest.main()
