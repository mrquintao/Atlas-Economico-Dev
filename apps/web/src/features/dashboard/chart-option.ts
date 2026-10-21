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
}

type Datum = [string, number, boolean];

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
}: Options): EChartsCoreOption {
  const data: Datum[] = observations.map((o) => [o.date, o.value, o.partial]);
  const isMonthly = frequency === "monthly";

  return {
    animationDuration: 300,
    aria: {
      enabled: true,
      label: {
        description: `Gráfico de linha: ${name} (${unit}), ${observations.length} observações.`,
      },
    },
    // Fixed margins (no containLabel): every chart gets the same plot area, so a given date
    // sits at the same horizontal position in all synchronised charts.
    grid: { left: 44, right: 16, top: 32, bottom: 72, containLabel: false },
    textStyle: { color: palette.text, fontFamily: "inherit" },
    tooltip: {
      trigger: "axis",
      backgroundColor: palette.tooltipBg,
      borderColor: palette.grid,
      textStyle: { color: palette.text },
      formatter: (params: unknown) => {
        const first = (Array.isArray(params) ? params[0] : params) as { data?: Datum } | undefined;
        if (!first?.data) return "";
        const [date, value, partial] = first.data;
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
