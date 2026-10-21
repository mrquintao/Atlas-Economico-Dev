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
  observations: Observation[];
  palette: ChartPalette;
}

type Datum = [string, number, boolean];

/** Pure builder for the ECharts option of a single-indicator time series. */
export function buildTimeSeriesOption({
  name,
  unit,
  frequency,
  observations,
  palette,
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
    grid: { left: 8, right: 16, top: 32, bottom: 72, containLabel: true },
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
        const when = isMonthly
          ? `${formatMonth(date)} — vigente em ${formatDate(date)}${partial ? " (mês parcial)" : ""}`
          : formatDate(date);
        return `<strong>${formatRate(value, unit)}</strong><br/>${when}`;
      },
    },
    xAxis: {
      type: "time",
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
        // The target only changes on Copom decisions: draw it as a step function.
        step: "end",
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
