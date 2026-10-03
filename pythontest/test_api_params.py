"""Check request parameters and the retained MeteoSwiss status output."""

import contextlib
import io
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import api_requester


class SourceRequestTests(unittest.TestCase):
    def test_rhine_request_uses_48_rows_and_descending_timestamp(self):
        source = next(s for s in api_requester.SOURCES if s["id"] == "basel_dataset_100089")
        response = MagicMock()
        response.status = 200
        response.headers = {}
        response.read.return_value = b'{"results": []}'
        response.__enter__.return_value = response
        with patch.object(api_requester, "urlopen", return_value=response) as urlopen:
            api_requester.read_response(source)
        request = urlopen.call_args.args[0]
        self.assertEqual(parse_qs(urlsplit(request.full_url).query), {
            "lang": ["en"], "limit": ["48"], "offset": ["0"], "order_by": ["-timestamp"],
        })

    def test_traffic_request_remains_at_10_rows(self):
        source = next(s for s in api_requester.SOURCES if s["id"] == "basel_dataset_100006")
        self.assertEqual(parse_qs(urlsplit(api_requester.source_url(source)).query)["limit"], ["10"])

    def test_meteoswiss_status_output_is_unchanged(self):
        source = next(s for s in api_requester.SOURCES if s["kind"] == "meteo_current")
        output = io.StringIO()
        with (
            patch.object(api_requester, "read_response", return_value=(
                200, {}, b"Station/Location;Date;tre200s0\nBAS;202610030800;15.2\n", None,
            )),
            patch.object(api_requester, "save_result"),
            patch.object(api_requester, "datetime", wraps=datetime) as clock,
            contextlib.redirect_stdout(output),
        ):
            clock.now.return_value = datetime(2026, 10, 3, 8, 10, tzinfo=timezone.utc)
            result = api_requester.check_meteoswiss_current(source)
        self.assertTrue(result["request_ok"])
        self.assertEqual(output.getvalue(),
            "MeteoSwiss Basel/Binningen temperature: OK — HTTP 200 — "
            "15.2 °C at 2026-10-03T10:00+02:00 (10.0 min old; Europe/Zurich)\n",
        )


if __name__ == "__main__":
    unittest.main()
