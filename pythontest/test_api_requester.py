"""Offline regression checks for MeteoSwiss parsing and status reporting."""

import contextlib
import io
import unittest
from unittest.mock import patch

import api_requester


class MeteoswissRateLimitTests(unittest.TestCase):
    def test_http_429_reports_rate_limit(self):
        source = next(
            source for source in api_requester.SOURCES
            if source["kind"] == "meteo_current"
        )
        cases = [
            ({"Retry-After": "60"}, "60"),
            ({"retry-after": "120"}, "120"),
            ({}, None),
        ]
        for headers, retry_after in cases:
            with self.subTest(headers=headers):
                output = io.StringIO()
                with (
                    patch.object(
                        api_requester, "read_response",
                        return_value=(429, headers, b"Too Many Requests", "HTTP 429"),
                    ),
                    patch.object(api_requester, "save_result") as save_result,
                    contextlib.redirect_stdout(output),
                ):
                    result = api_requester.check_meteoswiss_current(source)

                self.assertEqual(result["http_status"], 429)
                self.assertTrue(result["rate_limited"])
                self.assertFalse(result["request_ok"])
                self.assertEqual(result["retry_after"], retry_after)
                self.assertIn(
                    "FAILED — rate limited (HTTP 429; Retry-After: "
                    f"{retry_after or 'not provided'})",
                    output.getvalue(),
                )
                save_result.assert_called_once_with(source, result, None)


class MeteoswissPrecipitationTests(unittest.TestCase):
    def test_current_basel_precipitation_is_saved_without_inventing_missing_values(self):
        source = next(
            source for source in api_requester.SOURCES
            if source["kind"] == "meteo_current"
        )
        for raw_value, expected in (("0.70", 0.7), ("0.00", 0), ("-", None), ("", None)):
            with self.subTest(raw_value=raw_value):
                body = (
                    "Station/Location;Date;tre200s0;rre150z0;fu3010z0;fu3010z1;"
                    "gre000z0;ure200s0;sre000z0;tde200s0;dkl010z0;pp0qffs0;ppz850s0\n"
                    f"BAS;202610030810;14.60;{raw_value};4.3;11.0;326;67.5;10;6.1;26;1021;-\n"
                ).encode("cp1252")
                with (
                    patch.object(
                        api_requester, "read_response",
                        return_value=(200, {}, body, None),
                    ),
                    patch.object(api_requester, "save_result") as save_result,
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    result = api_requester.check_meteoswiss_current(source)

                self.assertTrue(result["request_ok"])
                measurements = result["data"]["station"]["measurements"]
                self.assertEqual(measurements["tre200s0"], 14.6)
                self.assertEqual(measurements["rre150z0"], expected)
                self.assertEqual(measurements["fu3010z1"], 11)
                self.assertEqual(measurements["gre000z0"], 326)
                self.assertEqual(measurements["ure200s0"], 67.5)
                self.assertEqual(measurements["pp0qffs0"], 1021)
                self.assertIsNone(measurements["ppz850s0"])
                self.assertEqual(result["data"]["station"]["measurement_count"], 9 if expected is None else 10)
                self.assertEqual(result["data"]["parameter_metadata"]["rre150z0"]["unit"], "mm")
                self.assertEqual(result["data"]["parameter_metadata"]["fu3010z1"]["unit"], "km/h")
                save_result.assert_called_once_with(source, result, None)


if __name__ == "__main__":
    unittest.main()
