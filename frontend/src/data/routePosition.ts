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

/** Preserve travelled progress on loops; only project when the road path changes. */
export function routeAnimationStart(
  previousRoute: Coordinates[],
  previousProgress: number,
  nextRoute: Coordinates[],
  nextProgress: number,
): number {
  const sameRoute =
    previousRoute.length === nextRoute.length &&
    previousRoute.every(
      (point, index) =>
        point[0] === nextRoute[index][0] && point[1] === nextRoute[index][1],
    );
  if (sameRoute)
    return nextProgress < previousProgress ? nextProgress : previousProgress;
  return routeProgress(
    nextRoute,
    routePosition(previousRoute, previousProgress),
  );
}

/** Locate a marker on a replacement route's shared prefix for continuous rerouting. */
export function routeProgress(
  route: Coordinates[],
  point: Coordinates,
): number {
  const lengths = route
    .slice(1)
    .map((end, index) => distance(route[index], end));
  const total = lengths.reduce((sum, length) => sum + length, 0);
  if (!total) return 0;
  const longitudeScale = Math.cos((point[1] * Math.PI) / 180);
  let bestDistance = Infinity;
  let bestProgress = 0;
  let travelled = 0;
  for (let index = 0; index < lengths.length; index++) {
    const start = route[index];
    const end = route[index + 1];
    const dx = (end[0] - start[0]) * longitudeScale;
    const dy = end[1] - start[1];
    const squared = dx * dx + dy * dy;
    const fraction = squared
      ? Math.max(
          0,
          Math.min(
            1,
            ((point[0] - start[0]) * longitudeScale * dx +
              (point[1] - start[1]) * dy) /
              squared,
          ),
        )
      : 0;
    const separation =
      ((point[0] - start[0]) * longitudeScale - fraction * dx) ** 2 +
      (point[1] - start[1] - fraction * dy) ** 2;
    if (separation < bestDistance) {
      bestDistance = separation;
      bestProgress = (travelled + lengths[index] * fraction) / total;
    }
    travelled += lengths[index];
  }
  return bestProgress;
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
