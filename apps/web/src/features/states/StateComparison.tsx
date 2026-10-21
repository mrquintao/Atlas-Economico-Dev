"use client";

import { LineChart } from "echarts/charts";
import {
  AriaComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useId, useMemo, useRef, useState } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { InlineError, LoadingState, RefreshingIndicator } from "@/components/ui/states";
import { useIndicators, useStateComparison } from "@/hooks/useObservations";
import { formatPeriod, formatValue } from "@/lib/format";
import { STATES } from "@/lib/states";
import type { StateComparison } from "@/types/api";

import { usePalette } from "../dashboard/TimeSeriesChart";
import { buildComparisonOption, type ComparisonSeries } from "./comparison-option";
import { resetsEachYear } from "./state-indicators";
import { DEFAULT_RANKING_CODE, RELATIVE_CODES } from "./StateRanking";
import { displayName, stateIndicatorOptions } from "./StateMap";
import { UfPicker } from "./UfPicker";

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, DataZoomComponent, AriaComponent, CanvasRenderer]);

export const MAX_COMPARISON_UFS = 6;
/** Initial example selection; any UF can be added or removed. */
export const DEFAULT_COMPARISON_UFS = ["SP", "MG", "RJ"];
const NO_RANGE = { start: null, end: null };

/** Historical series of one state indicator in up to six UFs, each as published. */
export function StateComparisonPanel() {
  const [code, setCode] = useState(DEFAULT_RANKING_CODE);
  const [selected, setSelected] = useState<string[]>(DEFAULT_COMPARISON_UFS);
  // An empty selection is never sent: the last valid one stays applied.
  const [applied, setApplied] = useState<string[]>(DEFAULT_COMPARISON_UFS);
  const catalog = useIndicators();
  const comparison = useStateComparison(code, applied, NO_RANGE);
  const options = useMemo(() => stateIndicatorOptions(catalog.data ?? []), [catalog.data]);

  function handleSelection(next: string[]) {
    setSelected(next);
    if (next.length > 0) setApplied(next);
  }

  const headingId = useId();
  const indicatorId = useId();
  const data =
    comparison.status === "error" && comparison.data?.indicator.code !== code ? null : comparison.data;

  return (
    <Card aria-labelledby={headingId}>
      <CardHeader>
        <h2 id={headingId} className="text-lg font-semibold">
          Evolução histórica
        </h2>
        <p className="text-sm text-muted-foreground">
          Compare a série de um indicador em até {MAX_COMPARISON_UFS} UFs. As cores seguem a ordem
          de seleção e não indicam desempenho.
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end gap-4">
          <label htmlFor={indicatorId} className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
            Indicador
            <select
              id={indicatorId}
              value={code}
              onChange={(event) => setCode(event.target.value)}
              className="rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground"
            >
              {options.length ? (
                <>
                  <optgroup label="Métricas relativas">
                    {options
                      .filter((o) => RELATIVE_CODES.includes(o.code))
                      .map((o) => (
                        <option key={o.code} value={o.code}>
                          {o.short_name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="Valores absolutos">
                    {options
                      .filter((o) => !RELATIVE_CODES.includes(o.code))
                      .map((o) => (
                        <option key={o.code} value={o.code}>
                          {o.short_name}
                        </option>
                      ))}
                  </optgroup>
                </>
              ) : (
                <option value={code}>{data?.indicator.short_name ?? code}</option>
              )}
            </select>
          </label>
          {comparison.status === "loading" && data && <RefreshingIndicator />}
        </div>
        <UfPicker
          legend={`UFs no gráfico (${selected.length} de no máximo ${MAX_COMPARISON_UFS})`}
          selected={selected}
          onChange={handleSelection}
          max={MAX_COMPARISON_UFS}
        />
        {selected.length === 0 && (
          <p role="alert" className="text-sm">
            Selecione ao menos uma UF. O gráfico abaixo mantém a seleção anterior.
          </p>
        )}
        {comparison.status === "error" && <InlineError message={comparison.error.message} onRetry={comparison.retry} />}
        {!data ? comparison.status !== "error" && <LoadingState /> : <ComparisonBody data={data} />}
      </CardContent>
    </Card>
  );
}

/** Accessible summary of the chart: which UFs have data, from when to when. */
export function comparisonSummary(data: StateComparison): string {
  const { indicator } = data;
  const parts = data.series.map((s) => {
    const obs = s.observations;
    if (!obs.length) return `${s.geography.acronym}: sem dado`;
    const first = formatPeriod(indicator.frequency, obs[0].date);
    const last = obs[obs.length - 1];
    return `${s.geography.acronym}: ${obs.length} valores de ${first} a ${formatPeriod(indicator.frequency, last.date)}, o último ${formatValue(last.value, indicator.unit)}`;
  });
  return `${indicator.short_name} por UF. ${parts.join("; ")}.`;
}

function ComparisonBody({ data }: { data: StateComparison }) {
  const { indicator } = data;
  const withData = data.series.filter((s) => s.observations.length > 0);
  const missing = data.series.filter((s) => s.observations.length === 0);
  const series: ComparisonSeries[] = useMemo(
    () =>
      data.series
        .filter((s) => s.observations.length > 0)
        .map((s) => ({ acronym: s.geography.acronym, observations: s.observations })),
    [data],
  );
  return (
    <>
      {withData.length > 0 ? (
        <ComparisonChart data={data} series={series} />
      ) : (
        <p className="rounded-lg border border-border p-5 text-sm text-muted-foreground">
          Nenhuma das UFs selecionadas tem valores de {indicator.short_name} armazenados.
        </p>
      )}
      {missing.length > 0 && (
        <p role="note" className="text-sm">
          Sem dado: {missing.map((s) => displayName(s.geography)).join(", ")}. Nenhum valor de{" "}
          {indicator.short_name} armazenado para{" "}
          {missing.length === 1 ? "essa UF" : "essas UFs"}; ausência de dado não equivale a zero.
        </p>
      )}
      {withData.length > 0 && <ComparisonTable data={data} />}
      <div className="flex flex-col gap-1.5 text-xs text-muted-foreground">
        <p>
          {indicator.name}. {data.accumulation_window}
        </p>
        {data.notes.map((note) => (
          <p key={note}>{note.startsWith("O Distrito Federal") ? `* ${note}` : note}</p>
        ))}
        <p>Fonte: Tesouro Nacional, SICONFI (RREO e RGF), valores como publicados.</p>
      </div>
    </>
  );
}

function ComparisonChart({ data, series }: { data: StateComparison; series: ComparisonSeries[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const palette = usePalette();
  const summary = comparisonSummary(data);
  const { unit, frequency, code } = data.indicator;

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
    const chart = chartRef.current;
    if (!chart || !palette) return;
    chart.setOption(
      buildComparisonOption({
        unit,
        frequency,
        series,
        palette,
        description: summary,
        resetsEachYear: resetsEachYear(code),
      }),
      { notMerge: true },
    );
  }, [unit, frequency, code, series, palette, summary]);

  return (
    <figure className="m-0">
      <div ref={containerRef} role="img" aria-label={summary} className="h-[360px] w-full sm:h-[420px]" />
    </figure>
  );
}

function ComparisonTable({ data }: { data: StateComparison }) {
  const { indicator } = data;
  const dates = [...new Set(data.series.flatMap((s) => s.observations.map((o) => o.date)))].toSorted().toReversed();
  const values = data.series.map((s) => new Map(s.observations.map((o) => [o.date, o.value])));
  const names = new Map(STATES.map((s) => [s.acronym, s.name]));
  return (
    <details className="text-sm">
      <summary className="cursor-pointer font-medium">Ver os valores em tabela</summary>
      <div className="mt-3 max-h-96 overflow-auto">
        <table className="w-full border-collapse text-left">
          <caption className="sr-only">
            {indicator.name} por período e UF ({indicator.unit})
          </caption>
          <thead>
            <tr className="border-b border-border text-xs text-muted-foreground">
              <th scope="col" className="py-1.5 pr-4 font-medium">
                Período
              </th>
              {data.series.map((s) => (
                <th key={s.geography.acronym} scope="col" className="py-1.5 pr-4 text-right font-medium">
                  <abbr title={names.get(s.geography.acronym)}>{s.geography.acronym}</abbr>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dates.map((date) => (
              <tr key={date} className="border-b border-border/60">
                <th scope="row" className="py-1.5 pr-4 font-normal">
                  {formatPeriod(indicator.frequency, date, true)}
                </th>
                {values.map((byDate, i) => {
                  const value = byDate.get(date);
                  return (
                    <td key={data.series[i].geography.acronym} className="py-1.5 pr-4 text-right tabular-nums">
                      {value === undefined ? "sem dado" : formatValue(value, indicator.unit)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
