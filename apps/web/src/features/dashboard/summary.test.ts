import { describe, expect, it } from "vitest";

import type { NationalDashboardItem, ObservationsResponse } from "@/types/api";

import { describeSeries, latestFromDashboard, referenceLabel, sourceSeriesLabel } from "./summary";

// Synthetic test data.
function item(partial: Partial<NationalDashboardItem>): NationalDashboardItem {
  return {
    indicator: {} as NationalDashboardItem["indicator"],
    status: "available",
    aggregation: { method: "last_value_of_period", description: "Último valor do mês." },
    latest: null,
    change_12m: null,
    ...partial,
  };
}

const latest = { date: "2026-10-21", value: 13.75, period_start: "2026-10-01", period_end: "2026-10-31", partial: true };

describe("latestFromDashboard", () => {
  it("returns null for an indicator without data instead of zero", () => {
    expect(latestFromDashboard(item({ status: "no_data" }))).toBeNull();
  });

  it("uses the server-computed 12-month change", () => {
    const change = { value: -1.25, change_unit: "p.p.", reference_date: "2025-10-31", reference_value: 15 };
    expect(latestFromDashboard(item({ latest, change_12m: change }))).toEqual({
      value: 13.75,
      date: "2026-10-21",
      change12m: -1.25,
      reference12m: "2025-10-31",
    });
  });

  it("omits the 12-month change when the API has no comparison", () => {
    expect(latestFromDashboard(item({ latest }))).toMatchObject({ change12m: null, reference12m: null });
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

  it("describes a fiscal series in its own periods and amounts in reais", () => {
    const response = {
      indicator: { short_name: "Receita corrente líquida" },
      unit: "R$ correntes",
      frequency: "bimonthly",
      observations: [],
      stats: {
        first: { date: "2018-01-01", value: 150e9 },
        last: { date: "2025-11-01", value: 266.2e9 },
        change: 116.2e9,
        change_unit: "R$ correntes",
        min: { date: "2018-01-01", value: 150e9 },
        max: { date: "2025-11-01", value: 266.2e9 },
      },
    } as unknown as ObservationsResponse;
    const text = describeSeries(response);
    expect(text).toContain("de 1º bim./2018 a 6º bim./2025");
    expect(text).toContain("passou de R$ 150,00 bi para R$ 266,20 bi (+R$ 116,20 bi)");
  });

  it("describes a series without statistics (year-to-date flows) by its last value only", () => {
    const point = (date: string, value: number) => ({ date, value, period_start: date, period_end: date, partial: false });
    const response = {
      indicator: { short_name: "Resultado primário" },
      unit: "R$ correntes",
      frequency: "bimonthly",
      stats: null,
      observations: [point("2024-01-01", 2e9), point("2025-11-01", -3.5e9)],
    } as unknown as ObservationsResponse;
    expect(describeSeries(response)).toBe(
      "Resultado primário de 1º bim./2024 a 6º bim./2025: 2 valores publicados; o último é -R$ 3,50 bi.",
    );
    expect(describeSeries({ ...response, observations: [] })).toBe(
      "Resultado primário: sem observações no período selecionado.",
    );
  });
});

describe("sourceSeriesLabel and the monthly reference prefix", () => {
  type Source = Parameters<typeof sourceSeriesLabel>[0];
  const bcb = { source: { acronym: "BCB" }, source_series_code: "432" } as Source;
  const ibge = { source: { acronym: "IBGE" }, source_series_code: "1737/2265" } as Source;
  const siconfi = { source: { acronym: "SICONFI" }, source_series_code: "RGF-Anexo 02" } as Source;

  it("names the official series by source", () => {
    expect(sourceSeriesLabel(bcb)).toBe("SGS 432");
    expect(sourceSeriesLabel(ibge)).toBe("SIDRA 1737 (v. 2265)");
    expect(sourceSeriesLabel(siconfi)).toBe("SICONFI, RGF-Anexo 02");
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
