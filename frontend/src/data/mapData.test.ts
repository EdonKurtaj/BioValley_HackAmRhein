import { afterEach, describe, expect, it, vi } from "vitest";
import { createMapDataSource, demoSnapshot, parseSnapshot } from "./mapData";

afterEach(() => vi.unstubAllGlobals());
describe("map API boundary", () => {
  it("works without a backend and labels demo data", async () => {
    expect(parseSnapshot(await createMapDataSource().load()).mode).toBe("demo");
  });
  it("loads the backend contract from the configured URL", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ...demoSnapshot, mode: "live" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    expect(
      (await createMapDataSource("https://example.com/api/").load()).mode,
    ).toBe("live");
    expect(fetchMock).toHaveBeenCalledWith("https://example.com/api/map", {
      signal: undefined,
    });
  });
  it("does not hide a backend failure with demo data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    );
    await expect(createMapDataSource("/api").load()).rejects.toThrow("503");
  });
  it("accepts an empty result", () => {
    expect(parseSnapshot({ ...demoSnapshot, locations: [] }).locations).toEqual(
      [],
    );
  });
  it.each([
    {
      ...demoSnapshot,
      locations: [{ ...demoSnapshot.locations[0], latitude: 91 }],
    },
    {
      ...demoSnapshot,
      locations: [{ ...demoSnapshot.locations[0], category: "unknown" }],
    },
    {
      ...demoSnapshot,
      locations: [demoSnapshot.locations[0], demoSnapshot.locations[0]],
    },
    { ...demoSnapshot, updatedAt: "yesterday" },
    { locations: [] },
  ])("rejects invalid external data", (input) => {
    expect(() => parseSnapshot(input)).toThrow();
  });
});
