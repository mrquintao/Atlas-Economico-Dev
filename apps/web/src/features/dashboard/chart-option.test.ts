import { describe, expect, it } from "vitest";

import { buildTimeSeriesOption } from "./chart-option";

const palette = { line: "#00f", area: "#00f1", text: "#000", muted: "#555", grid: "#eee", tooltipBg: "#fff" };

describe("buildTimeSeriesOption", () => {
  const option = buildTimeSeriesOption({
    name: "Meta Selic",
    unit: "% a.a.",
    frequency: "monthly",
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
  });

  it("formats tooltips in pt-BR and flags partial months", () => {
    const html = option.tooltip.formatter([{ data: ["2026-10-21", 13.75, true] }]);
    expect(html).toContain("13,75% a.a.");
    expect(html).toContain("out/2026");
    expect(html).toContain("21/10/2026");
    expect(html).toContain("mês parcial");
  });
});
