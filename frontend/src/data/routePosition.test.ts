import { describe, expect, it } from "vitest";
import { routePosition } from "./routePosition";

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
});
