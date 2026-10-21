"use client";

import { useMemo, useState } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useObservations } from "@/hooks/useObservations";
import { formatChange, formatDate, formatMonth, formatRate } from "@/lib/format";
import {
  DEFAULT_PRESET,
  isValidRange,
  rangeForPreset,
  SINCE_2008_START,
  todayLocalIso,
  type DateRange,
  type PeriodPreset,
} from "@/lib/period";

import { IndicatorCard, PlaceholderCard } from "./IndicatorCard";
import { MethodologyPanel } from "./MethodologyPanel";
import { PeriodFilter } from "./PeriodFilter";
import { describeSeries, latestFromMonthly } from "./summary";
import { TimeSeriesChart } from "./TimeSeriesChart";

const SELIC = "SELIC_TARGET";
const FULL_HISTORY: DateRange = { start: null, end: null };

export function Dashboard() {
  // One shared range for every chart on the page (charts are time-synchronised).
  const [preset, setPreset] = useState<PeriodPreset>(DEFAULT_PRESET);
  const [range, setRange] = useState<DateRange>({ start: SINCE_2008_START, end: null });
  const [frequency, setFrequency] = useState<"daily" | "monthly">("daily");
  const invalidRange = !isValidRange(range);
  // An invalid range is never sent to the API; the last valid one stays displayed.
  const [appliedRange, setAppliedRange] = useState<DateRange>(range);

  const latest = useObservations(SELIC, FULL_HISTORY, "monthly");
  const series = useObservations(SELIC, appliedRange, frequency);

  const latestSummary = useMemo(
    () => (latest.data ? latestFromMonthly(latest.data.observations) : null),
    [latest.data],
  );
  const indicator = latest.data?.indicator ?? series.data?.indicator ?? null;

  function updateRange(next: DateRange) {
    setRange(next);
    if (isValidRange(next)) setAppliedRange(next);
  }

  function handlePreset(next: Exclude<PeriodPreset, "custom">) {
    setPreset(next);
    // Relative presets ("5 anos") end at the latest official observation.
    const anchor = indicator?.last_stored_date ?? todayLocalIso();
    updateRange(rangeForPreset(next, anchor));
  }

  function handleCustomRange(next: DateRange) {
    setPreset("custom");
    updateRange(next);
  }

  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="highlights" className="flex flex-col gap-3">
        <h2 id="highlights" className="text-lg font-semibold">
          Indicadores em destaque
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {indicator ? (
            <IndicatorCard indicator={indicator} latest={latestSummary} />
          ) : latest.status === "error" ? (
            <Card className="p-5" role="alert">
              <h3 className="text-sm font-medium text-muted-foreground">Meta Selic</h3>
              <p className="mt-2 text-sm">{latest.error.message}</p>
            </Card>
          ) : (
            <Card className="p-5" aria-busy>
              <h3 className="text-sm font-medium text-muted-foreground">Meta Selic</h3>
              <div className="mt-3 h-8 w-32 animate-pulse rounded bg-muted" />
            </Card>
          )}
          <PlaceholderCard title="IPCA — 12 meses" note="Em implementação: próxima etapa do MVP." />
          <PlaceholderCard title="Dívida bruta / PIB" note="Em implementação: próxima etapa do MVP." />
        </div>
      </section>

      <Card aria-labelledby="chart-selic">
        <CardHeader>
          <h2 id="chart-selic" className="text-lg font-semibold">
            {indicator?.name ?? "Meta da taxa Selic"}
          </h2>
          {indicator && <p className="text-sm text-muted-foreground">{indicator.description}</p>}
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <PeriodFilter
            preset={preset}
            range={range}
            minDate={indicator?.first_stored_date ?? null}
            maxDate={indicator?.last_stored_date ?? null}
            frequency={frequency}
            onPresetChange={handlePreset}
            onCustomRange={handleCustomRange}
            onFrequencyChange={setFrequency}
            invalidRange={invalidRange}
          />
          <SeriesBody series={series} />
        </CardContent>
      </Card>
    </div>
  );
}

function SeriesBody({ series }: { series: ReturnType<typeof useObservations> }) {
  const data = series.data;
  if (series.status === "error" && !data) {
    return <ErrorState message={series.error.message} onRetry={series.retry} />;
  }
  if (!data) {
    return <LoadingState />;
  }
  const { stats, indicator, unit } = data;
  const fmtDate = data.frequency === "monthly" ? formatMonth : formatDate;

  return (
    <div className="flex flex-col gap-4" aria-busy={series.status === "loading"}>
      {series.status === "error" && (
        <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-red-700 dark:text-red-400">
          <span>{series.error.message} Exibindo os últimos dados carregados.</span>
          <button
            type="button"
            onClick={series.retry}
            className="rounded-md border border-border px-2 py-1 font-medium text-foreground hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
          >
            Tentar novamente
          </button>
        </div>
      )}
      {stats ? (
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <Stat label={`Início (${fmtDate(stats.first.date)})`} value={formatRate(stats.first.value, unit)} />
          <Stat label={`Fim (${fmtDate(stats.last.date)})`} value={formatRate(stats.last.value, unit)} />
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
          observations={data.observations}
          summary={describeSeries(data)}
        />
      )}
      <p className="text-xs text-muted-foreground">
        {data.aggregation.description} Use a roda do mouse, o gesto de pinça ou a barra inferior
        para ampliar o gráfico.
      </p>
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
