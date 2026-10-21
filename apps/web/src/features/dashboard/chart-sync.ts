/**
 * Synchronisation of cursor and zoom across the dashboard's ECharts instances, by date.
 *
 * echarts.connect matches tooltips by data index, which fails across series of different
 * lengths/frequencies, and combining it with this module made both re-trigger each other.
 */
import type { ECharts } from "echarts/core";

import type { Frequency } from "@/types/api";

/**
 * How a chart's points are dated. "day" = points dated by the actual day; the others = one point
 * per period, dated on the period's first day (SGS/SICONFI convention) but standing for the whole
 * period: a month, a bimester (RREO), a quarter, a four-month period (RGF) or a year.
 */
export type Granularity = "day" | "month" | "bimonthly" | "quarterly" | "four_monthly" | "annual";

const PERIOD_MONTHS: Record<Exclude<Granularity, "day">, number> = {
  month: 1,
  bimonthly: 2,
  quarterly: 3,
  four_monthly: 4,
  annual: 12,
};

/** Granularity of a plotted series: monthly values aggregated from a daily series are dated by day. */
export function granularityOf(frequency: Frequency, aggregated: boolean): Granularity {
  if (frequency === "daily" || aggregated) return "day";
  return frequency === "monthly" ? "month" : frequency;
}

export interface SyncedChartMeta {
  granularity: Granularity;
  /** Shared x-axis domain ("min/max"); null when the chart uses its own data extent. */
  domainKey: string | null;
  /** Time span (ms) the chart has data for; outside it the cursor shows no value. */
  extent: { min: number; max: number } | null;
}

/** Local-calendar time of an ISO date (ECharts parses "YYYY-MM-DD" in local time too). */
export function isoToTime(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).getTime();
}

/** Span covered by a series' first and last point; a period point covers the whole period. */
export function dataExtent(
  dates: string[],
  granularity: Granularity,
): { min: number; max: number } | null {
  const first = dates[0];
  const last = dates.at(-1);
  if (!first || !last) return null;
  const max = isoToTime(last);
  return {
    min: isoToTime(first),
    max: alignTime(max, granularity, "day"),
  };
}

/**
 * Maps a hovered time (ms, local calendar) from a source chart to the time to highlight in a
 * target chart. A period point first stands for its last day (its end-of-period position); that
 * day then maps to the target period containing it (never to the nearest one). So a day maps to
 * its month, a month to its last day, and a four-month period to its last bimester.
 */
export function alignTime(time: number, source: Granularity, target: Granularity): number {
  let date = new Date(time);
  if (source !== "day") {
    const size = PERIOD_MONTHS[source];
    const first = Math.floor(date.getMonth() / size) * size;
    date = new Date(date.getFullYear(), first + size, 0);
  }
  if (target === "day") return date.getTime();
  const size = PERIOD_MONTHS[target];
  return new Date(date.getFullYear(), Math.floor(date.getMonth() / size) * size, 1).getTime();
}

const charts = new Map<ECharts, SyncedChartMeta>();
let propagating = false;
/** Last zoom window applied by the user, re-applied to charts re-rendered on the same domain. */
let sharedZoom: { domainKey: string; start: number; end: number } | null = null;

function forOthers(source: ECharts, action: (chart: ECharts, meta: SyncedChartMeta) => void) {
  if (propagating) return;
  propagating = true;
  try {
    for (const [chart, meta] of charts) {
      if (chart !== source && !chart.isDisposed()) action(chart, meta);
    }
  } finally {
    propagating = false;
  }
}

interface AxisPointerEvent {
  axesInfo?: { axisDim: string; value: number }[];
}

function syncCursor(source: ECharts, event: AxisPointerEvent) {
  const sourceMeta = charts.get(source);
  const time = event.axesInfo?.find((a) => a.axisDim === "x")?.value;
  forOthers(source, (chart, meta) => {
    if (time === undefined || !sourceMeta) {
      chart.dispatchAction({ type: "hideTip" });
      return;
    }
    // No value to show where the target has no data (e.g. months not yet published):
    // otherwise ECharts would snap to the nearest existing point and mislabel the date.
    const extent = meta.extent;
    if (!extent || time < extent.min || time > extent.max) {
      chart.dispatchAction({ type: "hideTip" });
      return;
    }
    const target = alignTime(time, sourceMeta.granularity, meta.granularity);
    const x = chart.convertToPixel({ xAxisIndex: 0 }, target);
    if (Number.isFinite(x)) chart.dispatchAction({ type: "showTip", x, y: chart.getHeight() / 2 });
  });
}

function syncZoom(source: ECharts) {
  const domainKey = charts.get(source)?.domainKey;
  // Percentages only mean the same dates when the charts share the same x-axis domain.
  if (!domainKey) return;
  const option = source.getOption() as { dataZoom?: { start?: number; end?: number }[] };
  const zoom = option.dataZoom?.[0];
  if (zoom?.start === undefined || zoom.end === undefined) return;
  const { start, end } = zoom;
  sharedZoom = { domainKey, start, end };
  forOthers(source, (chart, meta) => {
    if (meta.domainKey === domainKey) chart.dispatchAction({ type: "dataZoom", start, end });
  });
}

/** Registers a chart; returns the function that unregisters it. */
export function registerChart(chart: ECharts, meta: SyncedChartMeta): () => void {
  charts.set(chart, meta);
  chart.on("updateAxisPointer", (event) => syncCursor(chart, event as AxisPointerEvent));
  chart.on("dataZoom", () => syncZoom(chart));
  chart.getZr().on("globalout", () => forOthers(chart, (c) => c.dispatchAction({ type: "hideTip" })));
  return () => {
    charts.delete(chart);
  };
}

/**
 * Call after (re)setting a chart's option: updates its metadata and re-applies the shared zoom
 * window when it is on the same domain (a new period starts unzoomed).
 */
export function afterOptionUpdate(chart: ECharts, meta: SyncedChartMeta) {
  charts.set(chart, meta);
  if (!sharedZoom || !meta.domainKey || sharedZoom.domainKey !== meta.domainKey) return;
  const { start, end } = sharedZoom;
  propagating = true;
  try {
    chart.dispatchAction({ type: "dataZoom", start, end });
  } finally {
    propagating = false;
  }
}
