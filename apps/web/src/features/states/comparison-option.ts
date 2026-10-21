import type { EChartsCoreOption } from "echarts/core";

import { formatAxisNumber, formatMonth, formatPeriod, formatValue, isCurrencyUnit } from "@/lib/format";
import type { Frequency, Observation } from "@/types/api";

import { currencyScale, toChartData, type ChartPalette } from "../dashboard/chart-option";

/**
 * Okabe–Ito colours (safe for colour blindness), assigned by selection order — never by value,
 * so no colour suggests a better or worse UF. Line style and marker also differ per UF.
 */
export const COMPARISON_COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"];
const LINE_TYPES = ["solid", "dashed", "dotted"] as const;
const SYMBOLS = ["circle", "rect", "triangle", "diamond", "roundRect", "pin"] as const;

export interface ComparisonSeries {
  label: string;
  /** Position of the UF in the selection (UFs without data included): sets colour and style. */
  index: number;
  observations: Observation[];
}

interface Options {
  unit: string;
  frequency: Frequency;
  series: ComparisonSeries[];
  palette: ChartPalette;
  description: string;
  /** Values accumulate from January: never join two different years. */
  resetsEachYear: boolean;
}

type Datum = [string, number | null, boolean];

interface TooltipParam {
  seriesName?: string;
  color?: string;
  data?: Datum;
}

/** Tooltip of the hovered period: each UF's value for that same period, or "sem dado". */
export function comparisonTooltip(params: TooltipParam[], unit: string, frequency: Frequency): string {
  const date = params.find((p) => p.data && p.data[1] !== null)?.data?.[0];
  if (!date) return "";
  const lines = params.map((p) => {
    const value = p.data && p.data[0] === date ? p.data[1] : null;
    return `${p.seriesName ?? ""}: ${value === null ? "sem dado" : formatValue(value, unit)}`;
  });
  return [`<strong>${formatPeriod(frequency, date, true)}</strong>`, ...lines].join("<br/>");
}

/** Pure builder for the ECharts option of one indicator in a few UFs (one line per UF). */
export function buildComparisonOption({
  unit,
  frequency,
  series,
  palette,
  description,
  resetsEachYear,
}: Options): EChartsCoreOption {
  const scale = isCurrencyUnit(unit)
    ? currencyScale(series.flatMap((s) => s.observations))
    : { factor: 1, label: "" };
  return {
    animationDuration: 300,
    aria: { enabled: true, label: { description } },
    grid: { left: 56, right: 16, top: 56, bottom: 72, containLabel: false },
    textStyle: { color: palette.text, fontFamily: "inherit" },
    legend: { top: 0, textStyle: { color: palette.text } },
    tooltip: {
      trigger: "axis",
      hideDelay: 0,
      backgroundColor: palette.tooltipBg,
      borderColor: palette.grid,
      textStyle: { color: palette.text },
      formatter: (params: unknown) =>
        comparisonTooltip((Array.isArray(params) ? params : [params]) as TooltipParam[], unit, frequency),
    },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: palette.grid } },
      axisLabel: { color: palette.muted, hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      name: scale.label ? `${unit}, em ${scale.label}` : unit,
      nameTextStyle: { color: palette.muted, align: "left" },
      // Zero baseline; extends below zero only if some value is negative. No log scale.
      min: (extent: { min: number }) => Math.min(0, extent.min),
      axisLabel: { color: palette.muted, formatter: (v: number) => formatAxisNumber(v / scale.factor) },
      splitLine: { lineStyle: { color: palette.grid, type: "dashed" } },
    },
    dataZoom: [
      { type: "inside", filterMode: "none" },
      {
        type: "slider",
        filterMode: "none",
        height: 24,
        bottom: 16,
        labelFormatter: (value: number) => formatMonth(new Date(value).toISOString().slice(0, 10)),
      },
    ],
    series: series.map((s) => ({
      name: s.label,
      type: "line",
      connectNulls: false,
      showSymbol: true,
      symbol: SYMBOLS[s.index % SYMBOLS.length],
      symbolSize: 6,
      color: COMPARISON_COLORS[s.index % COMPARISON_COLORS.length],
      lineStyle: { width: 2, type: LINE_TYPES[s.index % LINE_TYPES.length] },
      data: toChartData(s.observations, frequency, resetsEachYear),
    })),
  };
}
