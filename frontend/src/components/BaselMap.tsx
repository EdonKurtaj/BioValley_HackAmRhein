import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
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
  const map = useRef<L.Map | null>(null);
  const markers = useRef(new Map<string, L.Marker>());
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    if (!container.current) return;
    const instance = L.map(container.current, { zoomControl: false }).setView(
      BASEL_CENTER,
      BASEL_ZOOM,
    );
    map.current = instance;
    L.control.zoom({ position: "bottomright" }).addTo(instance);
    L.control
      .scale({ imperial: false, position: "bottomleft" })
      .addTo(instance);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    })
      .on("tileerror", () => setTileError(true))
      .addTo(instance);
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      instance.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map.current) return;
    const group = L.layerGroup().addTo(map.current);
    markers.current.clear();
    locations.forEach((location) => {
      const icon = L.divIcon({
        className: "location-marker",
        html: `<span class="pin pin-${location.category}">${categories[location.category].symbol}</span>`,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      });
      const popup = document.createElement("strong");
      popup.textContent = location.name;
      const marker = L.marker([location.latitude, location.longitude], {
        icon,
        title: location.name,
      })
        .bindPopup(popup)
        .on("click", () => onSelect(location.id))
        .addTo(group);
      markers.current.set(location.id, marker);
    });
    return () => {
      group.remove();
      markers.current.clear();
    };
  }, [locations, onSelect]);

  useEffect(() => {
    const marker = selectedId ? markers.current.get(selectedId) : undefined;
    if (marker) {
      map.current?.panTo(marker.getLatLng());
      marker.openPopup();
    } else map.current?.closePopup();
  }, [selectedId, locations]);

  useEffect(() => {
    map.current?.setView(BASEL_CENTER, BASEL_ZOOM);
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
          Kartenbilder konnten nicht vollständig geladen werden. Bitte
          Internetverbindung prüfen und die Seite neu laden.
        </div>
      )}
    </>
  );
}
