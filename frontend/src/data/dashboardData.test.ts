import { afterEach, describe, expect, it, vi } from "vitest";
import { loadDashboard, parseDashboard } from "./dashboardData";

const live = {
  mode: "live",
  updatedAt: "2026-10-03T10:00:00Z",
  locations: [],
  signals: [
    {
      id: "temperature",
      title: "Lufttemperatur",
      value: 33,
      unit: "°C",
      observedAt: "2026-10-03T09:50:00Z",
      freshness: "current",
      severity: "warning",
      source: "Supabase",
      detail: "Umgebung",
    },
  ],
  alerts: [],
  shipments: [],
  simulation: null,
  sourceLabel: "Supabase",
  transportSource: "Kein GPS-Feed",
};

afterEach(() => vi.unstubAllGlobals());
describe("dashboard provenance boundary", () => {
  it("accepts observed signals without inventing shipment telemetry", () => {
    expect(parseDashboard(live, "live").shipments).toEqual([]);
    expect(parseDashboard(live, "live").signals[0].value).toBe(33);
  });
  it("rejects a response from the wrong mode after switching feeds", () => {
    expect(() => parseDashboard(live, "demo")).toThrow();
  });
  it("rejects synthetic transports or replay clocks in live mode", () => {
    expect(() =>
      parseDashboard({ ...live, shipments: [{}] }, "live"),
    ).toThrow();
    expect(() =>
      parseDashboard({ ...live, simulation: { scenario: "fleet" } }, "live"),
    ).toThrow();
  });
  it("rejects invalid numeric signals", () => {
    expect(() =>
      parseDashboard({
        ...live,
        signals: [{ ...live.signals[0], value: Infinity }],
      }),
    ).toThrow();
  });
  it("does not include replay parameters in live requests", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => live });
    vi.stubGlobal("fetch", fetchMock);
    await loadDashboard("live", "urgent", 50, "2026-10-03T10:00:00Z");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/dashboard?mode=live");
  });
  it("keeps live feed failures visible", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503 }),
    );
    await expect(
      loadDashboard("live", "fleet", 0, "2026-10-03T10:00:00Z"),
    ).rejects.toThrow("Live-Daten nicht erreichbar");
  });
});
