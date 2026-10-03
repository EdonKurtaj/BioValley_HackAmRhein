import type { Coordinates } from "../interfaces";

function distance(a: Coordinates, b: Coordinates) {
  const radians = Math.PI / 180;
  const h =
    Math.sin(((b[1] - a[1]) * radians) / 2) ** 2 +
    Math.cos(a[1] * radians) *
      Math.cos(b[1] * radians) *
      Math.sin(((b[0] - a[0]) * radians) / 2) ** 2;
  return 2 * Math.asin(Math.min(1, Math.sqrt(h)));
}

/** Animate along the supplied corridor by distance; this does not estimate ETA. */
export function routePosition(
  route: Coordinates[],
  progress: number,
): Coordinates {
  if (route.length < 2 || !Number.isFinite(progress))
    throw new Error("Ungültige Route.");
  const lengths = route
    .slice(1)
    .map((point, index) => distance(route[index], point));
  const target =
    lengths.reduce((sum, length) => sum + length, 0) *
    Math.max(0, Math.min(1, progress));
  let travelled = 0;
  for (let index = 0; index < lengths.length; index++) {
    if (target <= travelled + lengths[index] && lengths[index] > 0) {
      const fraction = (target - travelled) / lengths[index];
      return [
        route[index][0] + (route[index + 1][0] - route[index][0]) * fraction,
        route[index][1] + (route[index + 1][1] - route[index][1]) * fraction,
      ];
    }
    travelled += lengths[index];
  }
  return route[route.length - 1];
}
