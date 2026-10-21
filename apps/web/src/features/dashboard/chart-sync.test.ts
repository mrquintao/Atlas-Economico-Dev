import { describe, expect, it } from "vitest";

import { alignTime, dataExtent, granularityOf, isoToTime } from "./chart-sync";

const t = (y: number, m: number, d: number) => new Date(y, m - 1, d).getTime();

describe("alignTime", () => {
  it("maps a day to the month that contains it, never to the nearest month", () => {
    // Regression: 27/03/2023 used to highlight the April 2023 point (nearest by distance).
    expect(alignTime(t(2023, 3, 27), "day", "month")).toBe(t(2023, 3, 1));
    expect(alignTime(t(2023, 3, 1), "day", "month")).toBe(t(2023, 3, 1));
    expect(alignTime(t(2023, 3, 31), "day", "month")).toBe(t(2023, 3, 1));
  });

  it("maps a month to its last day (end-of-month position) on a daily chart", () => {
    expect(alignTime(t(2024, 2, 1), "month", "day")).toBe(t(2024, 2, 29));
    expect(alignTime(t(2023, 12, 1), "month", "day")).toBe(t(2023, 12, 31));
  });

  it("keeps the time between charts of the same daily granularity", () => {
    expect(alignTime(t(2025, 4, 16), "day", "day")).toBe(t(2025, 4, 16));
  });

  it("keeps the month between monthly charts", () => {
    expect(alignTime(t(2025, 4, 1), "month", "month")).toBe(t(2025, 4, 1));
  });
});

describe("alignTime across fiscal periods (RREO bimesters, RGF four-month periods)", () => {
  it("maps a bimester to the four-month period that contains its last day", () => {
    // 6th bimester (nov–dez) → 3rd four-month period (set–dez), never the next year's first.
    expect(alignTime(t(2025, 11, 1), "bimonthly", "four_monthly")).toBe(t(2025, 9, 1));
    // 2nd bimester (mar–abr) → 1st four-month period (jan–abr).
    expect(alignTime(t(2025, 3, 1), "bimonthly", "four_monthly")).toBe(t(2025, 1, 1));
  });

  it("maps a four-month period to its last bimester", () => {
    expect(alignTime(t(2025, 9, 1), "four_monthly", "bimonthly")).toBe(t(2025, 11, 1));
    expect(alignTime(t(2025, 5, 1), "four_monthly", "bimonthly")).toBe(t(2025, 7, 1));
  });

  it("maps a day or a month to the bimester containing it", () => {
    expect(alignTime(t(2025, 12, 20), "day", "bimonthly")).toBe(t(2025, 11, 1));
    expect(alignTime(t(2025, 4, 1), "month", "four_monthly")).toBe(t(2025, 1, 1));
  });

  it("maps a period to its last day on a daily chart", () => {
    expect(alignTime(t(2025, 9, 1), "four_monthly", "day")).toBe(t(2025, 12, 31));
    expect(alignTime(t(2024, 1, 1), "bimonthly", "day")).toBe(t(2024, 2, 29));
  });
});

describe("granularityOf", () => {
  it("dates aggregated and daily series by day and period series by period", () => {
    expect(granularityOf("daily", false)).toBe("day");
    expect(granularityOf("monthly", true)).toBe("day");
    expect(granularityOf("monthly", false)).toBe("month");
    expect(granularityOf("bimonthly", false)).toBe("bimonthly");
    expect(granularityOf("four_monthly", false)).toBe("four_monthly");
  });
});

describe("dataExtent", () => {
  it("lets the last period of a fiscal series cover the whole period", () => {
    expect(dataExtent(["2018-01-01", "2025-09-01"], "four_monthly")).toEqual({
      min: t(2018, 1, 1),
      max: t(2025, 12, 31),
    });
  });

  it("lets the last month of a monthly series cover the whole month", () => {
    expect(dataExtent(["2006-12-01", "2026-08-01"], "month")).toEqual({
      min: t(2006, 12, 1),
      max: t(2026, 8, 31),
    });
  });

  it("ends a daily series at its last day and handles empty series", () => {
    expect(dataExtent(["2008-01-01", "2026-10-20"], "day")).toEqual({
      min: t(2008, 1, 1),
      max: t(2026, 10, 20),
    });
    expect(dataExtent([], "day")).toBeNull();
  });

  it("parses ISO dates in the local calendar", () => {
    expect(isoToTime("2026-09-15")).toBe(t(2026, 9, 15));
  });
});
