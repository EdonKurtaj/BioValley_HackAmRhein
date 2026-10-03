import { describe, expect, it } from "vitest";
import { routePosition, routeProgress } from "./routePosition";

describe("truck route replay", () => {
  const route: [number, number][] = [
    [7.5, 47.5],
    [7.51, 47.5],
    [7.55, 47.5],
  ];
  it("uses route distance rather than equal time per waypoint", () => {
    const position = routePosition(route, 0.5);
    expect(position[0]).toBeCloseTo(7.525, 4);
    expect(position[1]).toBe(47.5);
  });
  it("stays at endpoints outside replay progress", () => {
    expect(routePosition(route, -1)).toEqual(route[0]);
    expect(routePosition(route, 2)).toEqual(route[2]);
  });
  it("handles repeated route coordinates without dividing by zero", () => {
    expect(
      routePosition(
        [
          [7.5, 47.5],
          [7.5, 47.5],
        ],
        0.5,
      ),
    ).toEqual([7.5, 47.5]);
  });
  it("locates a truck on the shared prefix of a rerouted path", () => {
    const alternative: [number, number][] = [
      route[0],
      route[1],
      [7.51, 47.54],
      route[2],
    ];
    const truck = routePosition(route, 0.1);
    const progress = routeProgress(alternative, truck);
    expect(routePosition(alternative, progress)[0]).toBeCloseTo(truck[0], 9);
    expect(routePosition(alternative, progress)[1]).toBeCloseTo(truck[1], 9);
  });
  it("interpolates through a street corner instead of taking a diagonal", () => {
    const corner: [number, number][] = [
      [7.5, 47.5],
      [7.51, 47.5],
      [7.51, 47.51],
    ];
    const point = routePosition(corner, 0.5);
    expect(point[0]).toBeCloseTo(7.51, 8);
    expect(point[1]).toBeGreaterThan(47.5);
  });
});
