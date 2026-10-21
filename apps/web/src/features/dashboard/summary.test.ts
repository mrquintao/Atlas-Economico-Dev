import { describe, expect, it } from "vitest";

import type { Observation, ObservationsResponse } from "@/types/api";

import { describeSeries, latestFromMonthly, referenceLabel, sourceSeriesLabel } from "./summary";

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

describe("describeSeries", () => {
  it("uses months, not days, for every date of a monthly series", () => {
    const response = {
      indicator: { short_name: "Dívida bruta (DBGG)" },
      unit: "% do PIB",
      frequency: "monthly",
      stats: {
        first: { date: "2008-01-01", value: 57.51 },
        last: { date: "2026-08-01", value: 82.87 },
        change: 25.36,
        change_unit: "p.p.",
        min: { date: "2011-12-01", value: 51.27 },
        max: { date: "2020-10-01", value: 87.66 },
      },
    } as unknown as ObservationsResponse;
    const text = describeSeries(response);
    expect(text).toContain("de jan/2008 a ago/2026");
    expect(text).toContain("Mínima de 51,27% do PIB em dez/2011");
    expect(text).toContain("máxima de 87,66% do PIB em out/2020");
    expect(text).not.toMatch(/\d{2}\/\d{2}\/\d{4}/);
  });
});

describe("sourceSeriesLabel and the monthly reference prefix", () => {
  type Source = Parameters<typeof sourceSeriesLabel>[0];
  const bcb = { source: { acronym: "BCB" }, source_series_code: "432" } as Source;
  const ibge = { source: { acronym: "IBGE" }, source_series_code: "1737/2265" } as Source;

  it("names the official series by source", () => {
    expect(sourceSeriesLabel(bcb)).toBe("SGS 432");
    expect(sourceSeriesLabel(ibge)).toBe("SIDRA 1737 (v. 2265)");
  });

  it("uses the prefix for monthly series only", () => {
    expect(referenceLabel({ frequency: "monthly" }, "2026-09-01", "Referência:")).toBe(
      "Referência: set/2026",
    );
    expect(referenceLabel({ frequency: "monthly" }, "2026-09-01")).toBe("Posição de set/2026");
    expect(referenceLabel({ frequency: "daily" }, "2026-09-01", "Referência:")).toBe(
      "Vigente em 01/09/2026",
    );
  });
});
