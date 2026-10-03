import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
import type { Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { MapLocation, Shipment } from "../interfaces";
import { BASEL_CENTER, BASEL_ZOOM, categories } from "../config/map";
import { routePosition, routeProgress } from "../data/routePosition";
import { ShipmentDirections } from "../data/ShipmentDirections";
import { actionLabels } from "../config/dashboard";

// Vite must bundle the ESM worker and its shared imports as a separate asset.
maplibregl.setWorkerUrl(workerUrl);

export function BaselMap({
  locations,
  selectedId,
  onSelect,
  resetKey,
  shipments,
  selectedShipmentId,
  onSelectShipment,
}: {
  locations: MapLocation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  resetKey: number;
  shipments: Shipment[];
  selectedShipmentId: string | null;
  onSelectShipment: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const directions = useRef<ShipmentDirections | null>(null);
  const markers = useRef(new Map<string, Marker>());
  const truckMarkers = useRef(new Map<string, Marker>());
  const previousSelected = useRef<string | null>(null);
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
      truckMarkers.current.forEach((marker) => marker.remove());
      truckMarkers.current.clear();
      directions.current?.destroy();
      directions.current = null;
      instance.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!map.current) return;
    const ids = new Set(locations.map((location) => location.id));
    markers.current.forEach((marker, id) => {
      if (!ids.has(id)) {
        marker.remove();
        markers.current.delete(id);
      }
    });
    locations.forEach((location) => {
      const existing = markers.current.get(location.id);
      if (existing) {
        existing.setLngLat([location.longitude, location.latitude]);
        existing.getElement().setAttribute("aria-label", location.name);
        const content = document.createElement("strong");
        content.textContent = location.name;
        existing.getPopup().setDOMContent(content);
        return;
      }
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
  }, [locations, onSelect]);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const animations: number[] = [];
    let disposed = false;
    const ids = new Set(shipments.map((shipment) => shipment.id));
    truckMarkers.current.forEach((marker, id) => {
      if (!ids.has(id)) {
        marker.remove();
        truckMarkers.current.delete(id);
      }
    });
    for (const shipment of shipments) {
      let marker = truckMarkers.current.get(shipment.id);
      if (!marker) {
        const element = document.createElement("button");
        element.type = "button";
        const truck = document.createElement("span");
        truck.className = "truck-symbol";
        truck.textContent = "▰";
        const label = document.createElement("span");
        label.textContent = shipment.id;
        element.append(truck, label);
        element.addEventListener("click", () => onSelectShipment(shipment.id));
        marker = new maplibregl.Marker({ element })
          .setLngLat(routePosition(shipment.route, shipment.progress))
          .addTo(instance);
        truckMarkers.current.set(shipment.id, marker);
      }
      const position = marker.getLngLat();
      const from = routeProgress(shipment.route, [position.lng, position.lat]);
      const started = performance.now();
      const animate = (now: number) => {
        if (disposed) return;
        const fraction = Math.min(1, (now - started) / 800);
        marker!.setLngLat(
          routePosition(
            shipment.route,
            from + (shipment.progress - from) * fraction,
          ),
        );
        if (fraction < 1) animations.push(requestAnimationFrame(animate));
      };
      animations.push(requestAnimationFrame(animate));
      marker.getElement().className = `truck-marker action-${shipment.action} ${selectedShipmentId === shipment.id ? "selected" : ""}`;
      marker
        .getElement()
        .setAttribute(
          "aria-label",
          `Transport ${shipment.id}: ${actionLabels[shipment.action]}`,
        );
      marker
        .getElement()
        .setAttribute(
          "aria-pressed",
          String(selectedShipmentId === shipment.id),
        );
    }
    const selected = shipments.find(
      (shipment) => shipment.id === selectedShipmentId,
    );
    function updateRoutes() {
      directions.current ??= new ShipmentDirections(instance!);
      directions.current.showShipments(shipments, selectedShipmentId);
    }
    if (instance.isStyleLoaded()) updateRoutes();
    instance.on("load", updateRoutes);
    if (selected && previousSelected.current !== selected.id) {
      const bounds = new maplibregl.LngLatBounds();
      selected.route.forEach((point) => bounds.extend(point));
      instance.fitBounds(bounds, { padding: 75, maxZoom: 12, duration: 600 });
    }
    previousSelected.current = selected?.id ?? null;
    return () => {
      disposed = true;
      animations.forEach(cancelAnimationFrame);
      instance.off("load", updateRoutes);
    };
  }, [shipments, selectedShipmentId, onSelectShipment]);

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

  const selectedShipment = shipments.find(
    (shipment) => shipment.id === selectedShipmentId,
  );

  function focusRouteDifference() {
    if (!map.current || !selectedShipment) return;
    const activePoints = new Set(
      selectedShipment.route.map((point) => point.join(",")),
    );
    const otherPoints = new Set(
      selectedShipment.alternativeRoute.map((point) => point.join(",")),
    );
    const differences = [
      ...selectedShipment.route.filter(
        (point) => !otherPoints.has(point.join(",")),
      ),
      ...selectedShipment.alternativeRoute.filter(
        (point) => !activePoints.has(point.join(",")),
      ),
    ];
    const bounds = new maplibregl.LngLatBounds();
    (differences.length > 1 ? differences : selectedShipment.route).forEach(
      (point) => bounds.extend(point),
    );
    map.current.fitBounds(bounds, { padding: 85, maxZoom: 15, duration: 600 });
  }

  return (
    <>
      <div
        ref={container}
        className="map"
        aria-label="Interaktive Karte von Basel"
      />
      {selectedShipment && selectedShipment.alternativeRoute.length > 1 && (
        <div className="route-legend" role="status">
          <strong>
            {selectedShipment.id} ·{" "}
            {selectedShipment.routing?.rerouted
              ? "Umleitung aktiv"
              : "Umleitung geplant"}
          </strong>
          <span>
            {selectedShipment.routing?.rerouted
              ? "Grün: aktive Umleitung · blau gestrichelt: ursprüngliche Route"
              : "Abspielen: Wechsel nach 5 Demo-Minuten · blau gestrichelt: Alternative"}
          </span>
          <span>
            Gemeinsame Straßen bleiben gleich; die Abzweigung liegt weiter auf
            der Route.
          </span>
          <span>{selectedShipment.routing?.message}</span>
          <button
            type="button"
            className="text-button"
            onClick={focusRouteDifference}
          >
            Routenunterschied ansehen ↗
          </button>
        </div>
      )}
      {tileError && (
        <div className="tile-warning" role="status">
          Einige OpenStreetMap-Kartenausschnitte konnten nicht geladen werden.
          Bitte Internetverbindung prüfen und die Seite neu laden.
        </div>
      )}
    </>
  );
}
