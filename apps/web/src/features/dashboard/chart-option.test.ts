import { describe, expect, it } from "vitest";

import { buildTimeSeriesOption, toChartData } from "./chart-option";

const palette = { line: "#00f", area: "#00f1", text: "#000", muted: "#555", grid: "#eee", tooltipBg: "#fff" };

describe("buildTimeSeriesOption", () => {
  const option = buildTimeSeriesOption({
    name: "Meta Selic",
    unit: "% a.a.",
    frequency: "monthly",
    aggregated: true,
    step: true,
    domain: { min: "2008-01-01", max: "2026-10-21" },
    description: "Meta Selic de set/2026 a out/2026.",
    palette,
    observations: [
      { date: "2026-09-30", value: 13.75, period_start: "2026-09-01", period_end: "2026-09-30", partial: false },
      { date: "2026-10-21", value: 13.75, period_start: "2026-10-01", period_end: "2026-10-31", partial: true },
    ],
  }) as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

  it("plots values as a step series on a time axis starting at zero", () => {
    expect(option.xAxis.type).toBe("time");
    expect(option.yAxis.min).toBe(0);
    expect(option.yAxis.name).toBe("% a.a.");
    expect(option.series[0].step).toBe("end");
    expect(option.series[0].data).toEqual([
      ["2026-09-30", 13.75, false],
      ["2026-10-21", 13.75, true],
    ]);
  });

  it("marks only partial periods with a symbol", () => {
    const size = option.series[0].symbolSize;
    expect(size(["2026-09-30", 13.75, false])).toBe(0);
    expect(size(["2026-10-21", 13.75, true])).toBeGreaterThan(0);
  });

  it("enables zoom and accessible description", () => {
    expect(option.dataZoom.map((z: { type: string }) => z.type)).toEqual(["inside", "slider"]);
    expect(option.aria.enabled).toBe(true);
    expect(option.aria.label.description).toBe("Meta Selic de set/2026 a out/2026.");
  });

  it("formats tooltips in pt-BR and flags partial months", () => {
    const html = option.tooltip.formatter([{ data: ["2026-10-21", 13.75, true] }]);
    expect(html).toContain("13,75% a.a.");
    expect(html).toContain("out/2026");
    expect(html).toContain("21/10/2026");
    expect(html).toContain("mês parcial");
  });

  it("uses the shared x-axis domain", () => {
    expect(option.xAxis.min).toBe("2008-01-01");
    expect(option.xAxis.max).toBe("2026-10-21");
  });
});

describe("buildTimeSeriesOption for an original monthly series", () => {
  const option = buildTimeSeriesOption({
    name: "Dívida bruta (DBGG)",
    unit: "% do PIB",
    frequency: "monthly",
    aggregated: false,
    step: false,
    domain: null,
    description: "Dívida bruta (DBGG).",
    palette,
    observations: [
      { date: "2026-08-01", value: 82.87, period_start: "2026-08-01", period_end: "2026-08-31", partial: false },
    ],
  }) as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

  it("draws a regular line, not steps", () => {
    expect(option.series[0].step).toBe(false);
  });

  it("labels the tooltip with the reference month only", () => {
    const html = option.tooltip.formatter([{ data: ["2026-08-01", 82.87, false] }]);
    expect(html).toContain("82,87% do PIB");
    expect(html).toContain("Referência: ago/2026");
    expect(html).not.toContain("vigente");
  });
});

describe("toChartData", () => {
  // Synthetic test data.
  const month = (start: string, value: number) => ({
    date: start,
    value,
    period_start: start,
    period_end: start,
    partial: false,
  });

  it("breaks the line where a month is missing instead of bridging it", () => {
    const data = toChartData(
      [month("2024-01-01", 4.5), month("2024-02-01", 4.4), month("2024-05-01", 3.9)],
      "monthly",
    );
    expect(data).toEqual([
      ["2024-01-01", 4.5, false],
      ["2024-02-01", 4.4, false],
      ["2024-03-01", null, false],
      ["2024-05-01", 3.9, false],
    ]);
  });

  it("keeps contiguous series unchanged, across year ends and for daily data", () => {
    expect(
      toChartData([month("2023-12-01", 4.6), month("2024-01-01", 4.5)], "monthly"),
    ).toHaveLength(2);
    const day = (d: string) => ({ ...month(d, 1), period_end: d });
    expect(toChartData([day("2024-02-28"), day("2024-02-29"), day("2024-03-01")], "daily")).toHaveLength(3);
    expect(toChartData([day("2024-02-28"), day("2024-03-01")], "daily")[1]).toEqual([
      "2024-02-29",
      null,
      false,
    ]);
  });
});
