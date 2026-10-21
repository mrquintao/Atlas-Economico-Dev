"use client";

import { useState } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/segmented";
import {
  EmptyState,
  ErrorState,
  InlineError,
  LoadingState,
  RefreshingIndicator,
} from "@/components/ui/states";
import { useObservations, type ResourceState } from "@/hooks/useObservations";
import { formatValue, formatValueChange, isCurrencyUnit } from "@/lib/format";
import type { DateRange } from "@/lib/period";
import type { Indicator, ObservationsResponse } from "@/types/api";

import type { DashboardIndicator } from "./indicators";
import { MethodologyPanel } from "./MethodologyPanel";
import { describeSeries, formatReference } from "./summary";
import { TimeSeriesChart } from "./TimeSeriesChart";

const FREQUENCIES = [
  { value: "daily" as const, label: "Diária" },
  { value: "monthly" as const, label: "Mensal" },
];

interface Props {
  config: DashboardIndicator;
  /** Catalog metadata, when already loaded (used for the title before the series arrives). */
  indicator: Indicator | null;
  range: DateRange;
  domain: { min: string; max: string } | null;
}

/** One indicator's chart, statistics and methodology for the shared date range. */
export function IndicatorPanel({ config, indicator, range, domain }: Props) {
  const [frequency, setFrequency] = useState<"daily" | "monthly">("daily");
  const requested = config.frequencyToggle ? frequency : "original";
  const series = useObservations(config.code, range, requested);
  const meta = series.data?.indicator ?? indicator;
  const headingId = `chart-${config.code}`;

  return (
    <Card aria-labelledby={headingId}>
      <CardHeader>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-1">
            <h2 id={headingId} className="text-lg font-semibold">
              {meta?.name ?? config.fallbackName}
            </h2>
            {meta && <p className="text-sm text-muted-foreground">{meta.description}</p>}
          </div>
          {config.frequencyToggle && (
            <div className="flex shrink-0 flex-col gap-1">
              <span className="text-xs font-medium text-muted-foreground">Frequência</span>
              <Segmented
                label={`Frequência — ${meta?.short_name ?? config.fallbackName}`}
                options={FREQUENCIES}
                value={frequency}
                onChange={setFrequency}
              />
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <SeriesBody series={series} step={config.step} domain={domain} />
      </CardContent>
    </Card>
  );
}

interface SeriesBodyProps {
  series: ResourceState<ObservationsResponse> & { retry: () => void };
  step: boolean;
  domain: Props["domain"];
  /** Year-to-date flows: the chart does not join consecutive years. */
  resetsEachYear?: boolean;
  /** Extra notes shown above the aggregation description (e.g. the accumulation window). */
  notes?: string[];
}

/** Statistics, chart, aggregation note and methodology of one loaded series. */
export function SeriesBody({ series, step, domain, resetsEachYear = false, notes = [] }: SeriesBodyProps) {
  const data = series.data;
  if (series.status === "error" && !data) {
    return <ErrorState message={series.error.message} onRetry={series.retry} />;
  }
  if (!data) {
    return <LoadingState />;
  }
  const { stats, indicator, unit } = data;
  const aggregated = data.aggregation.method !== "none";
  const fmt = (date: string) => formatReference({ frequency: data.frequency }, date);
  // Amounts in current reais include inflation: say so, and call the change a difference.
  const currency = isCurrencyUnit(unit);

  return (
    <div className="flex flex-col gap-4" aria-busy={series.status === "loading"}>
      {series.status === "error" && (
        <InlineError
          message={`${series.error.message} Exibindo os últimos dados carregados.`}
          onRetry={series.retry}
        />
      )}
      {series.status === "loading" && <RefreshingIndicator />}
      {stats ? (
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <Stat label={`Início (${fmt(stats.first.date)})`} value={formatValue(stats.first.value, unit)} />
          <Stat label={`Fim (${fmt(stats.last.date)})`} value={formatValue(stats.last.value, unit)} />
          <Stat
            label={currency ? "Diferença no período (R$ correntes)" : "Variação no período"}
            value={formatValueChange(stats.change, stats.change_unit)} />
          <Stat
            label={currency ? "Mínima / máxima (R$ correntes)" : "Mínima / máxima"}
            value={`${formatValue(stats.min.value, unit)} / ${formatValue(stats.max.value, unit)}`}
          />
        </dl>
      ) : null}
      {data.count === 0 ? (
        <EmptyState message="Não há observações oficiais cujo período de referência termine no intervalo selecionado." />
      ) : (
        <TimeSeriesChart
          name={indicator.short_name}
          unit={unit}
          frequency={data.frequency}
          aggregated={aggregated}
          step={step}
          domain={domain}
          observations={data.observations}
          summary={describeSeries(data)}
          resetsEachYear={resetsEachYear}
        />
      )}
      {notes.map((note) => (
        <p key={note} className="text-xs text-muted-foreground">
          {note}
        </p>
      ))}
      <p className="text-xs text-muted-foreground">{data.aggregation.description}</p>
      <MethodologyPanel response={data} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-semibold tabular-nums">{value}</dd>
    </div>
  );
}
