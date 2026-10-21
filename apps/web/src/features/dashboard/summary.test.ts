import { describe, expect, it } from "vitest";

import type { Observation } from "@/types/api";

import { latestFromMonthly } from "./summary";

// Synthetic test data.
function month(periodStart: string, date: string, value: number): Observation {
  return { date, value, period_start: periodStart, period_end: periodStart, partial: false };
}

describe("latestFromMonthly", () => {
  it("returns null for an empty series instead of zero", () => {
    expect(latestFromMonthly([])).toBeNull();
  });

  it("computes the 12-month change in absolute terms", () => {
    const result = latestFromMonthly([
      month("2025-10-01", "2025-10-31", 15),
      month("2026-09-01", "2026-09-30", 13.75),
      month("2026-10-01", "2026-10-21", 13.75),
    ]);
    expect(result).toEqual({
      value: 13.75,
      date: "2026-10-21",
      change12m: -1.25,
      reference12m: "2025-10-31",
    });
  });

  it("omits the 12-month change when that month is missing", () => {
    expect(latestFromMonthly([month("2026-10-01", "2026-10-21", 13.75)])?.change12m).toBeNull();
  });
});
