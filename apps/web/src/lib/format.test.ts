import { describe, expect, it } from "vitest";

import {
  formatAxisNumber,
  formatChange,
  formatCurrency,
  formatDate,
  formatMonth,
  formatNumber,
  formatPeriod,
  formatRate,
  formatValue,
  formatValueChange,
  parseIsoDate,
} from "./format";

describe("format", () => {
  it("uses Brazilian decimal comma", () => {
    expect(formatNumber(13.75)).toBe("13,75");
    expect(formatNumber(1234.5)).toBe("1.234,50");
  });

  it("formats rate levels with their unit", () => {
    expect(formatRate(13.75, "% a.a.")).toBe("13,75% a.a.");
    expect(formatRate(76.1, "% do PIB")).toBe("76,10% do PIB");
    expect(formatRate(2, "índice")).toBe("2,00 índice");
  });

  it("expresses rate changes in percentage points with sign", () => {
    // 10% → 12% is +2 p.p., not +2% or +20%
    expect(formatChange(12 - 10, "p.p.")).toBe("+2,00 p.p.");
    expect(formatChange(-0.25, "p.p.")).toBe("-0,25 p.p.");
    expect(formatChange(0, "p.p.")).toBe("0,00 p.p.");
    expect(formatChange(-0.0000001, "p.p.")).toBe("0,00 p.p.");
  });

  it("formats ISO dates without timezone shifts", () => {
    expect(formatDate("2008-01-01")).toBe("01/01/2008");
    expect(formatDate("2026-10-21")).toBe("21/10/2026");
    expect(formatMonth("2024-02-29")).toBe("fev/2024");
  });

  it("rejects malformed dates", () => {
    expect(() => parseIsoDate("21/10/2026")).toThrow();
  });

  it("scales amounts in reais and writes the scale out", () => {
    expect(formatCurrency(266221395322.55)).toBe("R$ 266,22 bi");
    expect(formatCurrency(1_234_567_890_123)).toBe("R$ 1,23 tri");
    expect(formatCurrency(-5_120_000)).toBe("-R$ 5,12 mi");
    expect(formatCurrency(950.5)).toBe("R$ 950,50");
    expect(formatCurrency(0)).toBe("R$ 0,00");
    // The scale is chosen after rounding.
    expect(formatCurrency(999_999_999)).toBe("R$ 1,00 bi");
    expect(formatCurrency(-999_996_000, true)).toBe("-R$ 1,00 bi");
    expect(formatCurrency(999_994_000)).toBe("R$ 999,99 mi");
  });

  it("formats axis ticks with only the decimals they need", () => {
    expect(formatAxisNumber(0.5)).toBe("0,5");
    expect(formatAxisNumber(1)).toBe("1");
    expect(formatAxisNumber(1234.25)).toBe("1.234,25");
    expect(formatAxisNumber(-0)).toBe("0");
    expect(formatAxisNumber(-1e-16)).toBe("0");
  });

  it("signs differences in reais and never shows -0", () => {
    expect(formatCurrency(1_500_000_000, true)).toBe("+R$ 1,50 bi");
    expect(formatCurrency(-1_500_000_000, true)).toBe("-R$ 1,50 bi");
    expect(formatCurrency(-0.001, true)).toBe("R$ 0,00");
  });

  it("picks the format from the unit", () => {
    expect(formatValue(266221395322.55, "R$ correntes")).toBe("R$ 266,22 bi");
    expect(formatValue(45.1, "% da RCL ajustada")).toBe("45,10% da RCL ajustada");
    expect(formatValueChange(-2e9, "R$ correntes")).toBe("-R$ 2,00 bi");
    // Ratios change in percentage points, never in %.
    expect(formatValueChange(1.5, "p.p.")).toBe("+1,50 p.p.");
  });

  it("names reference periods in the frequency's own granularity", () => {
    expect(formatPeriod("daily", "2025-03-15")).toBe("15/03/2025");
    expect(formatPeriod("monthly", "2025-03-01")).toBe("mar/2025");
    expect(formatPeriod("bimonthly", "2025-11-01")).toBe("6º bim./2025");
    expect(formatPeriod("bimonthly", "2025-01-01", true)).toBe("1º bim./2025 (jan–fev)");
    expect(formatPeriod("four_monthly", "2025-09-01", true)).toBe("3º quadr./2025 (set–dez)");
    expect(formatPeriod("four_monthly", "2025-05-01")).toBe("2º quadr./2025");
    expect(formatPeriod("quarterly", "2025-04-01")).toBe("2º trim./2025");
    expect(formatPeriod("annual", "2025-01-01")).toBe("2025");
  });
});
