import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { MapLocation } from "../interfaces";
import { BASEL_CENTER, BASEL_ZOOM, categories } from "../config/map";

export function BaselMap({
  locations,
  selectedId,
  onSelect,
  resetKey,
}: {
  locations: MapLocation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  resetKey: number;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef(new Map<string, Marker>());
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    if (!container.current) return;
    const instance = new maplibregl.Map({
      container: container.current,
      center: BASEL_CENTER,
      zoom: BASEL_ZOOM,
      maxZoom: 19,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution:
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      attributionControl: false,
    });
    map.current = instance;
    instance.addControl(new maplibregl.NavigationControl(), "bottom-right");
    instance.addControl(
      new maplibregl.ScaleControl({ unit: "metric" }),
      "bottom-left",
    );
    instance.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right",
    );
    instance.on(
      "error",
      (event: maplibregl.ErrorEvent & { sourceId?: string }) => {
        if (event.sourceId === "osm") setTileError(true);
      },
    );
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      markers.current.forEach((marker) => marker.remove());
      markers.current.clear();
      instance.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map.current) return;
    markers.current.forEach((marker) => marker.remove());
    markers.current.clear();
    locations.forEach((location) => {
      const element = document.createElement("button");
      element.type = "button";
      element.className = "location-marker";
      element.setAttribute("aria-label", location.name);
      const pin = document.createElement("span");
      pin.className = `pin pin-${location.category}`;
      pin.textContent = categories[location.category].symbol;
      element.append(pin);

      const popupContent = document.createElement("strong");
      popupContent.textContent = location.name;
      const popup = new maplibregl.Popup({ offset: 22 }).setDOMContent(
        popupContent,
      );
      const marker = new maplibregl.Marker({ element, anchor: "bottom" })
        .setLngLat([location.longitude, location.latitude])
        .setPopup(popup)
        .addTo(map.current!);
      element.addEventListener("click", () => onSelect(location.id));
      markers.current.set(location.id, marker);
    });
    return () => {
      markers.current.forEach((marker) => marker.remove());
      markers.current.clear();
    };
  }, [locations, onSelect]);

  useEffect(() => {
    const marker = selectedId ? markers.current.get(selectedId) : undefined;
    if (marker) {
      const coordinates = marker.getLngLat();
      map.current?.easeTo({ center: coordinates, duration: 500 });
      if (!marker.getPopup()?.isOpen()) marker.togglePopup();
    } else markers.current.forEach((item) => item.getPopup().remove());
  }, [selectedId, locations]);

  useEffect(() => {
    map.current?.easeTo({ center: BASEL_CENTER, zoom: BASEL_ZOOM });
  }, [resetKey]);

  return (
    <>
      <div
        ref={container}
        className="map"
        aria-label="Interaktive Karte von Basel"
      />
      {tileError && (
        <div className="tile-warning" role="status">
          Einige OpenStreetMap-Kartenausschnitte konnten nicht geladen werden.
          Bitte Internetverbindung prüfen und die Seite neu laden.
        </div>
      )}
    </>
  );
}
