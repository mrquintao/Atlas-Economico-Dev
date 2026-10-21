import { describe, expect, it } from "vitest";

import { isValidRange, rangeForPreset, subtractYears, todayLocalIso } from "./period";

describe("period", () => {
  it("subtracts years handling leap days", () => {
    expect(subtractYears("2026-10-21", 5)).toBe("2021-10-21");
    expect(subtractYears("2024-02-29", 1)).toBe("2023-02-28");
  });

  it("anchors relative presets on the latest observation", () => {
    expect(rangeForPreset("5y", "2026-10-21")).toEqual({ start: "2021-10-21", end: null });
    expect(rangeForPreset("10y", "2026-10-21")).toEqual({ start: "2016-10-21", end: null });
    expect(rangeForPreset("since2008", "2026-10-21")).toEqual({ start: "2008-01-01", end: null });
    expect(rangeForPreset("all", "2026-10-21")).toEqual({ start: null, end: null });
  });

  it("validates ranges", () => {
    expect(isValidRange({ start: "2015-01-01", end: "2022-12-31" })).toBe(true);
    expect(isValidRange({ start: "2022-01-01", end: "2015-12-31" })).toBe(false);
    expect(isValidRange({ start: null, end: "2015-12-31" })).toBe(true);
  });

  it("uses the local calendar for today", () => {
    expect(todayLocalIso(new Date(2026, 9, 20, 23, 30))).toBe("2026-10-20");
  });
});
