import { describe, expect, it } from "vitest";

import type { Observation } from "@/types/api";

import { buildComparisonOption, COMPARISON_COLORS, comparisonTooltip } from "./comparison-option";

const PALETTE = { line: "#000", area: "#000", text: "#111", muted: "#555", grid: "#ddd", tooltipBg: "#fff" };

function bim(start: string, end: string, value: number): Observation {
  return { date: start, value, period_start: start, period_end: end, partial: false };
}

describe("buildComparisonOption", () => {
  const series = [
    { acronym: "SP", observations: [bim("2024-11-01", "2024-12-31", 9), bim("2025-01-01", "2025-02-28", 1)] },
    { acronym: "MG", observations: [bim("2024-11-01", "2024-12-31", 4)] },
  ];

  it("draws one line per UF, coloured by selection order, with distinct line styles", () => {
    const option = buildComparisonOption({
      unit: "R$ correntes",
      frequency: "bimonthly",
      series,
      palette: PALETTE,
      description: "x",
      resetsEachYear: false,
    }) as { color: string[]; series: { name: string; connectNulls: boolean; lineStyle: { type: string } }[] };
    expect(option.color).toEqual(COMPARISON_COLORS);
    expect(option.series.map((s) => s.name)).toEqual(["SP", "MG"]);
    expect(option.series.every((s) => s.connectNulls === false)).toBe(true);
    expect(option.series.map((s) => s.lineStyle.type)).toEqual(["solid", "dashed"]);
  });

  it("breaks year-to-date flows at each January", () => {
    const option = buildComparisonOption({
      unit: "R$ correntes",
      frequency: "bimonthly",
      series,
      palette: PALETTE,
      description: "x",
      resetsEachYear: true,
    }) as { series: { data: [string, number | null, boolean][] }[] };
    expect(option.series[0].data.map((d) => d[1])).toEqual([9, null, 1]);
  });
});

describe("comparisonTooltip", () => {
  it("shows each UF's value for the hovered period, or 'sem dado'", () => {
    const html = comparisonTooltip(
      [
        { seriesName: "SP", data: ["2025-01-01", 41.5, false] },
        { seriesName: "MG", data: ["2024-09-01", 48, false] },
      ],
      "% da RCL ajustada",
      "four_monthly",
    );
    expect(html).toBe(
      "<strong>1º quadr./2025 (jan–abr)</strong><br/>SP: 41,50% da RCL ajustada<br/>MG: sem dado",
    );
  });

  it("is empty over a break only", () => {
    expect(comparisonTooltip([{ seriesName: "SP", data: ["2025-01-01", null, false] }], "%", "bimonthly")).toBe("");
  });
});
