"""Street-path selection and continuity at a demo reroute."""

from dataclasses import replace
from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from risk_assessment.demo import _plans, _shipment, demo_fleet
from risk_assessment.dashboard import demo_dashboard
from risk_assessment.road_routes import ROAD_CACHE, edges, rank_routes, reroute_options, route_distance_km


def position(shipment):
    route = shipment["route"]
    target = route_distance_km(route) * shipment["progress"]
    travelled = 0.0
    for start, end in zip(route, route[1:]):
        length = route_distance_km([start, end])
        if length and target <= travelled + length:
            fraction = (target - travelled) / length
            return [a + (b - a) * fraction for a, b in zip(start, end)]
        travelled += length
    return route[-1]


class RoadRoutesTests(unittest.TestCase):
    anchor = datetime(2026, 10, 4, tzinfo=timezone.utc)

    def test_closure_rejects_the_fastest_route_and_selects_best_remaining_candidate(self):
        fast = {"duration_s": 10, "coordinates": [[0, 0], [1, 0], [2, 0]]}
        second = {"duration_s": 20, "coordinates": [[0, 0], [1, 1], [2, 0]]}
        third = {"duration_s": 30, "coordinates": [[0, 0], [1, 2], [2, 0]]}
        closed = ((0, 0), (1, 0))
        self.assertEqual(rank_routes([third, fast, second], blocked_edges={closed}), [second, third])
        self.assertEqual(rank_routes([fast], blocked_edges={closed}), [])
        self.assertEqual(rank_routes([second, fast], delay_seconds={closed: 25})[0], second)

    def test_cached_paths_are_full_street_geometry_and_have_shared_endpoints(self):
        for record in ROAD_CACHE["shipments"].values():
            for candidate in record["routes"]:
                self.assertGreater(len(candidate["coordinates"]), 50)
                self.assertGreater(candidate["duration_s"], 0)
                self.assertEqual(candidate["coordinates"][0], record["routes"][0]["coordinates"][0])
                self.assertEqual(candidate["coordinates"][-1], record["routes"][0]["coordinates"][-1])

    def test_reroute_keeps_the_truck_position_and_updates_eta_and_distance(self):
        before = demo_fleet(self.anchor, 4.999, "reroute")["shipments"][0]
        after = demo_fleet(self.anchor, 5, "reroute")["shipments"][0]
        for a, b in zip(position(before), position(after)):
            self.assertAlmostEqual(a, b, places=10)
        self.assertEqual(before["action"], "reroute")
        self.assertTrue(after["routing"]["rerouted"])
        self.assertEqual(after["status"], "moving")
        self.assertLess(after["etaAt"], before["etaAt"])
        self.assertNotEqual(before["route"], after["route"])
        self.assertGreater(after["slackMinutes"], before["slackMinutes"])
        self.assertGreater(after["distanceKm"], before["distanceKm"])
        self.assertGreater(after["remainingKm"], 0)
        at_end = demo_fleet(self.anchor, 180, "reroute")["shipments"][0]
        self.assertEqual(at_end["progress"], 1)
        self.assertEqual(at_end["remainingKm"], 0)
        self.assertEqual(position(at_end), at_end["route"][-1])

    def test_selected_alternative_avoids_the_closed_directed_segment(self):
        plan = _plans("reroute")[0]
        option = reroute_options(plan)
        closed_end = tuple(option["blocked_location"])
        closed = next(edge for edge in edges(plan.coordinates) if edge[1] == closed_end)
        self.assertNotIn(closed, edges(option["coordinates"]))

    def test_reroute_keeps_its_trigger_visible_without_scoring_the_avoided_closure(self):
        before = demo_dashboard(self.anchor, 0, "reroute")
        after = demo_dashboard(self.anchor, 10, "reroute")
        before_location = next(point for point in before["locations"] if point["id"] == "jam-BV-104")
        after_location = next(point for point in after["locations"] if point["id"] == "jam-BV-104")
        self.assertEqual(before_location["longitude"], after_location["longitude"])
        self.assertEqual(before_location["latitude"], after_location["latitude"])
        self.assertIn("Umfahrene Demo-Sperrung", after_location["name"])
        self.assertEqual(after["signals"][1]["value"], 0)
        self.assertIn("umfahren", after["signals"][1]["detail"])
        self.assertEqual(after["shipments"][0]["score"]["components"]["route"], 0)
        self.assertIn("45 min", after["shipments"][0]["routing"]["message"])

    def test_absent_alternative_keeps_primary_and_does_not_invent_a_reroute(self):
        with patch("risk_assessment.demo.reroute_options", return_value=None):
            shipment = demo_fleet(self.anchor, 10, "reroute")["shipments"][0]
        self.assertFalse(shipment["routing"]["rerouted"])
        self.assertIsNone(shipment["alternateEtaAt"])
        self.assertNotEqual(shipment["action"], "reroute")
        self.assertEqual(shipment["alternativeRoute"], ())

    def test_slow_alternative_and_quality_hold_cannot_trigger_a_switch(self):
        plan = _plans("reroute")[0]
        option = reroute_options(plan)
        with patch("risk_assessment.demo.reroute_options", return_value={**option, "remaining_minutes": 500}):
            shipment = _shipment(plan, self.anchor, 10, allow_reroute=True)
        self.assertFalse(shipment["routing"]["rerouted"])
        self.assertNotEqual(shipment["action"], "reroute")
        held = _shipment(replace(plan, start_c=7, ambient_c=40), self.anchor, 10, allow_reroute=True)
        self.assertEqual(held["action"], "quality_review")
        self.assertFalse(held["routing"]["rerouted"])
        self.assertEqual(held["route"], plan.coordinates)


if __name__ == "__main__":
    unittest.main()
