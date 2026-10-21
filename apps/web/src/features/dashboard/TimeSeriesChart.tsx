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
  observations: Observation[];
  /** Short textual summary for assistive technology. */
  summary: string;
}

export function TimeSeriesChart({ name, unit, frequency, observations, summary }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const palette = usePalette();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const chart = echarts.init(container, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(container);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current || !palette) return;
    chartRef.current.setOption(
      buildTimeSeriesOption({ name, unit, frequency, observations, palette }),
      { notMerge: true },
    );
  }, [name, unit, frequency, observations, palette]);

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
