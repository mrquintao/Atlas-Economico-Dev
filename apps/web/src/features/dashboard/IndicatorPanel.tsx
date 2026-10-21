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
import { useObservations } from "@/hooks/useObservations";
import { formatChange, formatRate } from "@/lib/format";
import type { DateRange } from "@/lib/period";
import type { Indicator } from "@/types/api";

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
        <SeriesBody series={series} config={config} domain={domain} />
      </CardContent>
    </Card>
  );
}

function SeriesBody({
  series,
  config,
  domain,
}: {
  series: ReturnType<typeof useObservations>;
  config: DashboardIndicator;
  domain: Props["domain"];
}) {
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
          <Stat label={`Início (${fmt(stats.first.date)})`} value={formatRate(stats.first.value, unit)} />
          <Stat label={`Fim (${fmt(stats.last.date)})`} value={formatRate(stats.last.value, unit)} />
          <Stat label="Variação no período" value={formatChange(stats.change, stats.change_unit)} />
          <Stat
            label="Mínima / máxima"
            value={`${formatRate(stats.min.value, unit)} / ${formatRate(stats.max.value, unit)}`}
          />
        </dl>
      ) : null}
      {data.count === 0 ? (
        <EmptyState message="Não há observações oficiais armazenadas para o período selecionado." />
      ) : (
        <TimeSeriesChart
          name={indicator.short_name}
          unit={unit}
          frequency={data.frequency}
          aggregated={aggregated}
          step={config.step}
          domain={domain}
          observations={data.observations}
          summary={describeSeries(data)}
        />
      )}
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
