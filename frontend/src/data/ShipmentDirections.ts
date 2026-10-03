import MapLibreGlDirections, {
  layersFactory,
  type Feature,
  type LineString,
} from "@maplibre/maplibre-gl-directions";
import type { Map } from "maplibre-gl";
import type { Shipment } from "../interfaces";

/** Load server-planned road paths into Directions without a request on every replay tick.
 * Uses the plugin's documented subclass/load-and-save customization mechanism.
 */
export class ShipmentDirections extends MapLibreGlDirections {
  constructor(map: Map) {
    const outline = getComputedStyle(document.documentElement)
      .getPropertyValue("--marker-outline")
      .trim();
    const layers = layersFactory().map((layer) => {
      if (layer.type !== "line" || !layer.id.includes("routeline"))
        return layer;
      const alternative = layer.id.includes("alt-routeline");
      const casing = layer.id.endsWith("casing");
      return {
        ...layer,
        layout: {
          ...layer.layout,
          "line-join": "round" as const,
          "line-cap": "round" as const,
        },
        paint: {
          "line-color": casing ? outline : ["get", "color"],
          "line-width": casing ? 8 : ["case", ["get", "selected"], 6, 3],
          "line-opacity": casing
            ? 0.5
            : ["case", ["get", "selected"], 0.9, 0.45],
          ...(alternative ? { "line-dasharray": [2, 2] } : {}),
        },
      } as typeof layer;
    });
    super(map, {
      layers,
      requestOptions: {
        alternatives: "3",
        overview: "full",
        geometries: "geojson",
      },
    });
    this.interactive = false;
    this.hoverable = false;
  }

  showShipments(shipments: Shipment[], selectedId: string | null) {
    const css = getComputedStyle(document.documentElement);
    const features: Feature<LineString>[] = shipments.map((shipment) => ({
      type: "Feature",
      geometry: { type: "LineString", coordinates: shipment.route },
      properties: {
        route: "SELECTED",
        selected: shipment.id === selectedId,
        color: css
          .getPropertyValue(
            shipment.action === "quality_review"
              ? "--danger-ink"
              : shipment.action === "buffer" || shipment.action === "expedite"
                ? "--warning-ink"
                : "--green",
          )
          .trim(),
      },
    }));
    const selected = shipments.find((shipment) => shipment.id === selectedId);
    if (selected && selected.alternativeRoute.length > 1)
      features.push({
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: selected.alternativeRoute,
        },
        properties: {
          route: "ALT",
          selected: true,
          color: css.getPropertyValue("--water-ink").trim(),
        },
      });
    this.routelines = [features];
    this.draw();
  }
}
