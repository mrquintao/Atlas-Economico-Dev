import type { EChartsCoreOption } from "echarts/core";

import {
  formatDate,
  formatMonth,
  formatNumber,
  formatPeriod,
  formatValue,
  isCurrencyUnit,
} from "@/lib/format";
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
  /** Values accumulate from January (year-to-date flows): never join two different years. */
  resetsEachYear?: boolean;
}

type Datum = [string, number | null, boolean];

const MONTHS_PER_PERIOD: Partial<Record<Frequency, number>> = {
  monthly: 1,
  bimonthly: 2,
  quarterly: 3,
  four_monthly: 4,
  annual: 12,
};

/** Start of the period that follows ``periodStart`` (next day, month, bimester…), as ISO date. */
function nextPeriodStart(periodStart: string, frequency: Frequency): string {
  const d = new Date(`${periodStart}T00:00:00Z`);
  if (frequency === "daily") d.setUTCDate(d.getUTCDate() + 1);
  else d.setUTCMonth(d.getUTCMonth() + (MONTHS_PER_PERIOD[frequency] ?? 1));
  return d.toISOString().slice(0, 10);
}

/**
 * Chart points with an explicit break (null value) wherever a period is missing between two
 * observations, so that gaps in the official series are drawn as gaps, never bridged. With
 * `resetsEachYear` (values accumulated from January), consecutive years are not joined either:
 * a line from December's total to January's would suggest a fall that is only the restart.
 */
export function toChartData(
  observations: Observation[],
  frequency: Frequency,
  resetsEachYear = false,
): Datum[] {
  const data: Datum[] = [];
  observations.forEach((o, i) => {
    const previous = observations[i - 1];
    if (previous) {
      const expected = nextPeriodStart(previous.period_start, frequency);
      if (o.period_start > expected) {
        data.push([expected, null, false]);
      } else if (resetsEachYear && o.period_start.slice(0, 4) !== previous.period_start.slice(0, 4)) {
        data.push([o.period_start, null, false]);
      }
    }
    data.push([o.date, o.value, o.partial]);
  });
  return data;
}

/** Scale of the y-axis labels of amounts in reais, chosen from the largest absolute value. */
function currencyScale(observations: Observation[]): { factor: number; label: string } {
  const max = Math.max(0, ...observations.map((o) => Math.abs(o.value)));
  if (max >= 1e12) return { factor: 1e12, label: "trilhões" };
  if (max >= 1e9) return { factor: 1e9, label: "bilhões" };
  if (max >= 1e6) return { factor: 1e6, label: "milhões" };
  return { factor: 1, label: "" };
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
  resetsEachYear = false,
}: Options): EChartsCoreOption {
  const data = toChartData(observations, frequency, resetsEachYear);
  const isMonthly = frequency === "monthly";
  // Bimonthly, four-monthly… series have few points: each one gets a marker, so even a single
  // published period is visible.
  const sparse = frequency !== "daily" && frequency !== "monthly";
  const currency = isCurrencyUnit(unit);
  const scale = currency ? currencyScale(observations) : { factor: 1, label: "" };

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
        const when = sparse
          ? `Referência: ${formatPeriod(frequency, date, true)}`
          : !isMonthly
            ? formatDate(date)
            : aggregated
              ? `${formatMonth(date)} — vigente em ${formatDate(date)}${partialNote}`
              : `Referência: ${formatMonth(date)}${partialNote}`;
        return `<strong>${formatValue(value, unit)}</strong><br/>${when}`;
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
      name: scale.label ? `${unit}, em ${scale.label}` : unit,
      nameTextStyle: { color: palette.muted, align: "left" },
      scale: false,
      // Zero baseline for rates; extends below zero only if the series has negative values.
      min: (extent: { min: number }) => Math.min(0, extent.min),
      axisLabel: { color: palette.muted, formatter: (v: number) => formatNumber(v / scale.factor, 0) },
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
          return frequency === "daily" ? formatDate(iso) : formatMonth(iso);
        },
      },
    ],
    series: [
      {
        name,
        type: "line",
        step: step ? "end" : false,
        // Partial periods (e.g. the running month) get a larger hollow marker; daily and monthly
        // series show no other markers.
        showSymbol: true,
        symbol: "emptyCircle",
        symbolSize: (value: Datum) => (value[2] ? 8 : sparse ? 5 : 0),
        connectNulls: false,
        lineStyle: { width: 2, color: palette.line },
        itemStyle: { color: palette.line },
        areaStyle: { color: palette.area },
        data,
      },
    ],
  };
}
