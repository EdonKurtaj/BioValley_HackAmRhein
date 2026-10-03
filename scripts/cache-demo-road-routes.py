"""Refresh reproducible OSM street geometry for the synthetic fleet (internet required)."""

from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    fleet = json.loads((ROOT / "config/demo-transports.json").read_text())
    shipments = {}
    for shipment in fleet["shipments"]:
        start, end = shipment["coordinates"][0], shipment["coordinates"][-1]
        points = ";".join(",".join(str(number) for number in point) for point in (start, end))
        query = urlencode({"alternatives": "3", "geometries": "geojson", "overview": "full", "steps": "false"})
        url = f"https://router.project-osrm.org/route/v1/driving/{points}?{query}"
        with urlopen(url, timeout=30) as response:
            payload = json.load(response)
        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise ValueError(f"No road route for {shipment['id']}")
        shipments[shipment["id"]] = {
            "request": url,
            "routes": [{"coordinates": route["geometry"]["coordinates"],
                        "distance_m": route["distance"], "duration_s": route["duration"]}
                       for route in payload["routes"]],
        }
        print(f"{shipment['id']}: {len(payload['routes'])} road candidates")
    cache = {"source": "OSRM driving / OpenStreetMap", "fetched_at": datetime.now(timezone.utc).isoformat(),
             "shipments": shipments}
    path = ROOT / "config/demo-road-routes.json"
    # Compact geometry keeps the cached dataset small; never overwrite with a partial fetch.
    path.write_text(json.dumps(cache, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
