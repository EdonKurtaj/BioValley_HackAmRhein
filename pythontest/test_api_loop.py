"""Offline checks that isolated errors do not stop source polling."""

import contextlib
import io
import sys
import unittest
from unittest.mock import MagicMock, patch

import api_requester
import transform_port_pegel


class PollingResilienceTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(api_requester, "create_ingestor", return_value=None))
        self.output = io.StringIO()
        self.enterContext(contextlib.redirect_stdout(self.output))
        self.enterContext(patch.object(transform_port_pegel, "transform", return_value={}))
        self.enterContext(patch.object(
            transform_port_pegel, "save",
            return_value=api_requester.DATA_DIR / "port_pegel_clean" / "latest.json",
        ))

    def test_source_error_does_not_skip_remaining_sources_or_next_cycle(self):
        first_source = api_requester.SOURCES[0]

        def check_source(source):
            if source is first_source:
                raise AttributeError("Unexpected source payload")
            return {"source_id": source["id"]}

        with (
            patch.object(api_requester, "check_source", side_effect=check_source) as check,
            patch.object(api_requester.time, "sleep"),
        ):
            for _ in range(2):
                results = api_requester.run_cycle()
                self.assertEqual(
                    [r["source_id"] for r in results],
                    [s["id"] for s in api_requester.SOURCES[1:]],
                )
        self.assertEqual(
            [call.args[0] for call in check.call_args_list], api_requester.SOURCES * 2,
        )
        self.assertEqual(self.output.getvalue().count("FAILED — AttributeError: Unexpected source payload"), 2)
        self.assertEqual(self.output.getvalue().count("Clean port data saved:"), 2)

    def test_unexpected_transform_error_is_reported_with_type(self):
        with (
            patch.object(api_requester, "check_source", return_value={}),
            patch.object(api_requester.time, "sleep"),
            patch.object(transform_port_pegel, "transform", side_effect=TypeError("Unexpected table")),
        ):
            self.assertEqual(len(api_requester.run_cycle()), len(api_requester.SOURCES))
        self.assertIn("Clean port data: FAILED — TypeError: Unexpected table", self.output.getvalue())

    def test_unexpected_transform_import_error_is_reported(self):
        original_import = __import__

        def import_module(name, *args, **kwargs):
            if name == "transform_port_pegel":
                raise ImportError("Broken dependency")
            return original_import(name, *args, **kwargs)

        with (
            patch.object(api_requester, "check_source", return_value={}),
            patch.object(api_requester.time, "sleep"),
            patch("builtins.__import__", side_effect=import_module),
        ):
            self.assertEqual(len(api_requester.run_cycle()), len(api_requester.SOURCES))
        self.assertIn("Clean port data: FAILED — ImportError: Broken dependency", self.output.getvalue())

    def test_watch_sleeps_and_retries_after_unexpected_cycle_error(self):
        with (
            patch.object(sys, "argv", ["api_requester.py", "--interval", "7"]),
            patch.object(api_requester, "run_cycle", side_effect=[TypeError("Unexpected cycle"), [], KeyboardInterrupt]) as cycle,
            patch.object(api_requester.time, "sleep") as sleep,
            patch.object(api_requester.time, "monotonic", side_effect=[0, 0, 0, 7, 7, 14]),
        ):
            self.assertEqual(api_requester.main(), 0)
        self.assertEqual(cycle.call_count, 3)
        self.assertEqual([call.args for call in sleep.call_args_list], [(7,), (7,)])
        self.assertIn("Cycle: FAILED — TypeError: Unexpected cycle", self.output.getvalue())
        self.assertIn("Stopped.", self.output.getvalue())

    def test_watch_continues_after_source_error(self):
        intervals = 0

        def sleep(seconds):
            nonlocal intervals
            if seconds == 7:
                intervals += 1
                if intervals == 2:
                    raise KeyboardInterrupt

        def check_source(source):
            if source is api_requester.SOURCES[0]:
                raise TypeError("Unexpected source")
            return {"source_id": source["id"]}

        with (
            patch.object(sys, "argv", ["api_requester.py", "--interval", "7"]),
            patch.object(api_requester, "check_source", side_effect=check_source) as check,
            patch.object(api_requester.time, "sleep", side_effect=sleep),
            patch.object(api_requester.time, "monotonic", side_effect=[0, 0, 0, 7, 7]),
        ):
            self.assertEqual(api_requester.main(), 0)
        self.assertEqual(check.call_count, 2 * len(api_requester.SOURCES))
        self.assertIn("Stopped.", self.output.getvalue())

    def test_road_traffic_polls_each_minute_without_repolling_regular_sources(self):
        clock = 0
        cycles = []
        traffic = [source for source in api_requester.SOURCES if source["kind"] == "opentransportdata"]

        def collect(_ingestor, *, sources=None):
            nonlocal clock
            cycles.append((clock, api_requester.SOURCES if sources is None else sources))
            if clock >= 600:
                raise KeyboardInterrupt
            started = clock
            clock += 20  # Collection duration must not add drift to the interval.
            if started == 60:
                raise RuntimeError("Temporary traffic failure")

        def sleep(seconds):
            nonlocal clock
            clock += seconds

        with (
            patch.object(sys, "argv", ["api_requester.py"]),
            patch.object(api_requester, "run_cycle", side_effect=collect),
            patch.object(api_requester.time, "sleep", side_effect=sleep),
            patch.object(api_requester.time, "monotonic", side_effect=lambda: clock),
        ):
            self.assertEqual(api_requester.main(), 0)
        self.assertEqual(cycles[0], (0, api_requester.SOURCES))
        self.assertEqual(cycles[-1], (600, api_requester.SOURCES))
        self.assertEqual(cycles[1:-1], [(minute * 60, traffic) for minute in range(1, 10)])
        self.assertIn("Temporary traffic failure", self.output.getvalue())

    def test_traffic_cycle_uses_existing_ingestion_and_skips_port_transform(self):
        traffic = [source for source in api_requester.SOURCES if source["kind"] == "opentransportdata"]
        sink = MagicMock()
        result = {"source_id": traffic[0]["id"], "request_ok": True}
        with (
            patch.object(api_requester, "check_source", return_value=result) as check,
            patch.object(api_requester.time, "sleep"),
            patch.object(transform_port_pegel, "transform") as transform,
        ):
            self.assertEqual(api_requester.run_cycle(sink, sources=traffic), [result])
        check.assert_called_once_with(traffic[0])
        sink.flush.assert_called_once_with()
        sink.ingest.assert_called_once_with(traffic[0], result)
        transform.assert_not_called()

    def test_keyboard_interrupt_is_not_swallowed_by_source_or_transform(self):
        for stage in ("source", "transform"):
            with self.subTest(stage=stage):
                with (
                    patch.object(api_requester, "check_source", side_effect=KeyboardInterrupt if stage == "source" else None, return_value={}),
                    patch.object(transform_port_pegel, "transform", side_effect=KeyboardInterrupt if stage == "transform" else None, return_value={}),
                    patch.object(api_requester.time, "sleep"),
                ):
                    with self.assertRaises(KeyboardInterrupt):
                        api_requester.run_cycle()


if __name__ == "__main__":
    unittest.main()
