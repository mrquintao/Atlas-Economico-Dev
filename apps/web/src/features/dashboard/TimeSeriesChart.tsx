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
import { afterOptionUpdate, dataExtent, registerChart, type SyncedChartMeta } from "./chart-sync";

echarts.use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, AriaComponent, CanvasRenderer]);

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
  /** Textual summary of the series, used as the chart's accessible name. */
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
    const unregister = registerChart(chart, { granularity: "day", domainKey: null, extent: null });
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(container);
    return () => {
      observer.disconnect();
      unregister();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !palette) return;
    chart.setOption(
      buildTimeSeriesOption({
        name,
        unit,
        frequency,
        aggregated,
        observations,
        palette,
        step,
        domain,
        description: summary,
      }),
      { notMerge: true },
    );
    // Original monthly series are dated on the 1st but stand for the whole month.
    const granularity = frequency === "monthly" && !aggregated ? "month" : "day";
    const meta: SyncedChartMeta = {
      granularity,
      domainKey: domain ? `${domain.min}/${domain.max}` : null,
      extent: dataExtent(
        observations.map((o) => o.date),
        granularity,
      ),
    };
    afterOptionUpdate(chart, meta);
  }, [name, unit, frequency, aggregated, observations, palette, step, domain, summary]);

  return (
    <figure className="m-0">
      {/* ECharts' aria component labels this element with `summary` (see chart-option). */}
      <div ref={containerRef} role="img" aria-label={summary} className="h-[360px] w-full sm:h-[420px]" />
    </figure>
  );
}
