// MapLibre uses [longitude, latitude]; locations are illustrative, not measured.
export const BASEL_CENTER: [number, number] = [7.5886, 47.5596];
export const BASEL_ZOOM = 11.2;
export const categories = {
  port: { label: "Logistik", symbol: "↗" },
  river: { label: "Rhein", symbol: "≈" },
  weather: { label: "Wetter", symbol: "☀" },
  traffic: { label: "Verkehr", symbol: "!" },
} as const;
