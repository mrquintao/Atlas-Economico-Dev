"use client";

import { LineChart } from "echarts/charts";
import {
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef, useState } from "react";

import type { Frequency, Observation } from "@/types/api";

import { buildTimeSeriesOption, type ChartPalette } from "./chart-option";

echarts.use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, AriaComponent, CanvasRenderer]);

/**
 * Synchronisation of cursor and zoom across the dashboard's charts, by date. (echarts.connect
 * matches by data index, which fails across series of different lengths/frequencies, and
 * combining both mechanisms makes them re-trigger each other.)
 */
const syncedCharts = new Set<echarts.ECharts>();
let propagating = false;

interface AxisPointerEvent {
  axesInfo?: { axisDim: string; value: number }[];
}

function forOthers(source: echarts.ECharts, action: (chart: echarts.ECharts) => void) {
  if (propagating) return;
  propagating = true;
  try {
    for (const chart of syncedCharts) {
      if (chart !== source && !chart.isDisposed()) action(chart);
    }
  } finally {
    propagating = false;
  }
}

function syncCursor(source: echarts.ECharts, event: AxisPointerEvent) {
  const time = event.axesInfo?.find((a) => a.axisDim === "x")?.value;
  forOthers(source, (chart) => {
    if (time === undefined) {
      chart.dispatchAction({ type: "hideTip" });
      return;
    }
    const x = chart.convertToPixel({ xAxisIndex: 0 }, time);
    if (Number.isFinite(x)) chart.dispatchAction({ type: "showTip", x, y: chart.getHeight() / 2 });
  });
}

function syncZoom(source: echarts.ECharts) {
  const option = source.getOption() as { dataZoom?: { start?: number; end?: number }[] };
  const zoom = option.dataZoom?.[0];
  if (zoom?.start === undefined || zoom.end === undefined) return;
  // All charts share the same x-axis domain, so the same percentages are the same dates.
  forOthers(source, (chart) =>
    chart.dispatchAction({ type: "dataZoom", start: zoom.start, end: zoom.end }),
  );
}

function hideOthers(source: echarts.ECharts) {
  forOthers(source, (chart) => chart.dispatchAction({ type: "hideTip" }));
}

function readPalette(): ChartPalette {
  const css = getComputedStyle(document.documentElement);
  const v = (name: string) => css.getPropertyValue(name).trim();
  return {
    line: v("--chart-line"),
    area: v("--chart-area"),
    text: v("--foreground"),
    muted: v("--muted-foreground"),
    grid: v("--border"),
    tooltipBg: v("--card"),
  };
}

function usePalette(): ChartPalette | null {
  const [palette, setPalette] = useState<ChartPalette | null>(null);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setPalette(readPalette());
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return palette;
}

interface Props {
  name: string;
  unit: string;
  frequency: Frequency;
  aggregated: boolean;
  step: boolean;
  domain: { min: string; max: string } | null;
  observations: Observation[];
  /** Short textual summary for assistive technology. */
  summary: string;
}

export function TimeSeriesChart({
  name,
  unit,
  frequency,
  aggregated,
  step,
  domain,
  observations,
  summary,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const palette = usePalette();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart = echarts.init(container, undefined, { renderer: "canvas" });
    syncedCharts.add(chart);
    chart.on("updateAxisPointer", (event) => syncCursor(chart, event as AxisPointerEvent));
    chart.on("dataZoom", () => syncZoom(chart));
    chart.getZr().on("globalout", () => hideOthers(chart));
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(container);
    return () => {
      observer.disconnect();
      syncedCharts.delete(chart);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current || !palette) return;
    chartRef.current.setOption(
      buildTimeSeriesOption({
        name,
        unit,
        frequency,
        aggregated,
        observations,
        palette,
        step,
        domain,
      }),
      { notMerge: true },
    );
  }, [name, unit, frequency, aggregated, observations, palette, step, domain]);

  return (
    <figure className="m-0">
      <div
        ref={containerRef}
        role="img"
        aria-label={summary}
        className="h-[360px] w-full sm:h-[420px]"
      />
      <figcaption className="sr-only">{summary}</figcaption>
    </figure>
  );
}
