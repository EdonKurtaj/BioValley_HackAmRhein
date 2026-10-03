"""Offline regression checks for source status reporting."""

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


if __name__ == "__main__":
    unittest.main()
