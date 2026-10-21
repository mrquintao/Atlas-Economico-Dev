import type { EChartsCoreOption } from "echarts/core";

import { formatDate, formatMonth, formatNumber, formatRate } from "@/lib/format";
import type { Frequency, Observation } from "@/types/api";

export interface ChartPalette {
  line: string;
  area: string;
  text: string;
  muted: string;
  grid: string;
  tooltipBg: string;
}

interface Options {
  name: string;
  unit: string;
  frequency: Frequency;
  /** True when monthly values were derived from a daily series (last value of each month). */
  aggregated: boolean;
  observations: Observation[];
  palette: ChartPalette;
  /** Step line for levels that only change by decision (e.g. the Selic target). */
  step: boolean;
  /** Shared x-axis domain (ISO dates) so that all charts on the page line up in time. */
  domain: { min: string; max: string } | null;
  /** Accessible description (ECharts sets it as the container's aria-label). */
  description: string;
}

type Datum = [string, number | null, boolean];

/** Start of the period that follows ``periodStart`` (next day or next month), as ISO date. */
function nextPeriodStart(periodStart: string, frequency: Frequency): string {
  const d = new Date(`${periodStart}T00:00:00Z`);
  if (frequency === "daily") d.setUTCDate(d.getUTCDate() + 1);
  else d.setUTCMonth(d.getUTCMonth() + 1);
  return d.toISOString().slice(0, 10);
}

/**
 * Chart points with an explicit break (null value) wherever a period is missing between two
 * observations, so that gaps in the official series are drawn as gaps, never bridged.
 */
export function toChartData(observations: Observation[], frequency: Frequency): Datum[] {
  const data: Datum[] = [];
  observations.forEach((o, i) => {
    const previous = observations[i - 1];
    if (previous && (frequency === "daily" || frequency === "monthly")) {
      const expected = nextPeriodStart(previous.period_start, frequency);
      if (o.period_start > expected) data.push([expected, null, false]);
    }
    data.push([o.date, o.value, o.partial]);
  });
  return data;
}

/** Pure builder for the ECharts option of a single-indicator time series. */
export function buildTimeSeriesOption({
  name,
  unit,
  frequency,
  aggregated,
  observations,
  palette,
  step,
  domain,
  description,
}: Options): EChartsCoreOption {
  const data = toChartData(observations, frequency);
  const isMonthly = frequency === "monthly";

  return {
    animationDuration: 300,
    aria: {
      enabled: true,
      label: { description },
    },
    // Fixed margins (no containLabel): every chart gets the same plot area, so a given date
    // sits at the same horizontal position in all synchronised charts.
    grid: { left: 44, right: 16, top: 32, bottom: 72, containLabel: false },
    textStyle: { color: palette.text, fontFamily: "inherit" },
    tooltip: {
      trigger: "axis",
      // Hide immediately: a lingering tooltip from the previous date would pair wrong values
      // while the synchronised cursor moves into a range without data.
      hideDelay: 0,
      backgroundColor: palette.tooltipBg,
      borderColor: palette.grid,
      textStyle: { color: palette.text },
      formatter: (params: unknown) => {
        const first = (Array.isArray(params) ? params[0] : params) as { data?: Datum } | undefined;
        if (!first?.data) return "";
        const [date, value, partial] = first.data;
        if (value === null) return ""; // break inserted for a missing period
        const partialNote = partial ? " (mês parcial)" : "";
        const when = !isMonthly
          ? formatDate(date)
          : aggregated
            ? `${formatMonth(date)} — vigente em ${formatDate(date)}${partialNote}`
            : `Referência: ${formatMonth(date)}${partialNote}`;
        return `<strong>${formatRate(value, unit)}</strong><br/>${when}`;
      },
    },
    xAxis: {
      type: "time",
      min: domain?.min,
      max: domain?.max,
      axisLine: { lineStyle: { color: palette.grid } },
      axisLabel: { color: palette.muted, hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: unit,
      nameTextStyle: { color: palette.muted, align: "left" },
      scale: false,
      min: 0,
      axisLabel: { color: palette.muted, formatter: (v: number) => formatNumber(v, 0) },
      splitLine: { lineStyle: { color: palette.grid, type: "dashed" } },
    },
    dataZoom: [
      { type: "inside", filterMode: "none" },
      {
        type: "slider",
        filterMode: "none",
        height: 24,
        bottom: 16,
        labelFormatter: (value: number) => {
          const iso = new Date(value).toISOString().slice(0, 10);
          return isMonthly ? formatMonth(iso) : formatDate(iso);
        },
      },
    ],
    series: [
      {
        name,
        type: "line",
        step: step ? "end" : false,
        // Only partial periods (e.g. the running month) get a hollow marker.
        showSymbol: true,
        symbol: "emptyCircle",
        symbolSize: (value: Datum) => (value[2] ? 8 : 0),
        connectNulls: false,
        lineStyle: { width: 2, color: palette.line },
        itemStyle: { color: palette.line },
        areaStyle: { color: palette.area },
        data,
      },
    ],
  };
}
