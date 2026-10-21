"use client";

import { useMemo, useState } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ErrorState, InlineError, LoadingState } from "@/components/ui/states";
import { useStateDashboard, useStateIndicators, type ResourceState } from "@/hooks/useObservations";
import {
  isValidRange,
  rangeForPreset,
  startOfMonth,
  todayLocalIso,
  type DateRange,
  type PeriodPreset,
} from "@/lib/period";
import type { Indicator, StateIndicatorSeries, StateIndicators } from "@/types/api";

import { SeriesBody } from "../dashboard/IndicatorPanel";
import { PeriodFilter } from "../dashboard/PeriodFilter";
import { resetsEachYear } from "./state-indicators";
import { StateIndicatorCard } from "./StateIndicatorCard";

/** State series start in 2018 at the earliest: the whole history is the default period. */
const STATE_DEFAULT_PRESET: PeriodPreset = "all";

interface StoredBounds {
  first: string | null;
  last: string | null;
}

/** Earliest first and latest last stored date of the UF across its state indicators. */
export function stateBounds(indicators: Indicator[]): StoredBounds {
  const firsts = indicators.flatMap((i) => (i.first_stored_date ? [i.first_stored_date] : []));
  const lasts = indicators.flatMap((i) => (i.last_stored_date ? [i.last_stored_date] : []));
  return {
    first: firsts.length ? firsts.reduce((a, b) => (a < b ? a : b)) : null,
    last: lasts.length ? lasts.reduce((a, b) => (a > b ? a : b)) : null,
  };
}

interface Props {
  /** UF acronym (validated by the page). */
  uf: string;
  name: string;
}

/** Fiscal panel of one UF: latest values, explicit absences and synchronised charts. */
export function StateDashboard({ uf, name }: Props) {
  const [preset, setPreset] = useState<PeriodPreset>(STATE_DEFAULT_PRESET);
  const [range, setRange] = useState<DateRange>({ start: null, end: null });
  const invalidRange = !isValidRange(range);
  // An invalid range is never sent to the API; the last valid one stays displayed.
  const [appliedRange, setAppliedRange] = useState<DateRange>(range);

  const dashboard = useStateDashboard(uf);
  const series = useStateIndicators(uf, appliedRange);

  // Availability, notes and stored dates do not depend on the range: take them from whichever
  // response arrived first.
  const notes = dashboard.data?.notes ?? series.data?.notes ?? [];
  const catalog = useMemo(
    () =>
      dashboard.data?.indicators.map((i) => ({ indicator: i.indicator, status: i.status })) ??
      series.data?.indicators.map((i) => ({ indicator: i.indicator, status: i.status })) ??
      null,
    [dashboard.data, series.data],
  );
  const missing = catalog?.filter((i) => i.status === "no_data") ?? [];
  const noData = catalog !== null && missing.length === catalog.length;
  const bounds = useMemo(
    () => stateBounds(catalog?.map((i) => i.indicator) ?? []),
    [catalog],
  );

  // Same x-axis for every chart, so the same period sits at the same horizontal position.
  const domain = useMemo(() => {
    const min = appliedRange.start ? startOfMonth(appliedRange.start) : bounds.first;
    const max = appliedRange.end ?? bounds.last;
    return min && max ? { min, max } : null;
  }, [appliedRange.start, appliedRange.end, bounds.first, bounds.last]);

  function updateRange(next: DateRange) {
    setRange(next);
    if (isValidRange(next)) setAppliedRange(next);
  }

  function handlePreset(next: Exclude<PeriodPreset, "custom">) {
    setPreset(next);
    updateRange(rangeForPreset(next, bounds.last ?? todayLocalIso()));
  }

  function handleCustomRange(next: DateRange) {
    setPreset("custom");
    updateRange(next);
  }

  return (
    <div className="flex flex-col gap-8">
      {notes.length > 0 && (
        <aside
          aria-labelledby="state-notes"
          className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-100"
        >
          <h2 id="state-notes" className="font-semibold">
            Ressalva de comparabilidade
          </h2>
          {notes.map((note) => (
            <p key={note} className="mt-1">
              {note}
            </p>
          ))}
        </aside>
      )}

      <section aria-labelledby="state-highlights" className="flex flex-col gap-3">
        <h2 id="state-highlights" className="text-lg font-semibold">
          Últimos valores publicados
        </h2>
        <Highlights dashboard={dashboard} name={name} />
      </section>

      {missing.length > 0 && !noData && (
        <section aria-labelledby="state-missing" className="flex flex-col gap-2">
          <h2 id="state-missing" className="text-lg font-semibold">
            Indicadores sem dados para {name}
          </h2>
          <p className="text-sm text-muted-foreground">
            Não há valores armazenados destes indicadores para a UF. Eles não são estimados nem
            exibidos como zero.
          </p>
          <ul className="list-disc pl-5 text-sm">
            {missing.map(({ indicator }) => (
              <li key={indicator.code}>{indicator.short_name}</li>
            ))}
          </ul>
        </section>
      )}

      {!noData && (
        <>
          <section aria-labelledby="state-period" className="flex flex-col gap-3">
            <h2 id="state-period" className="sr-only">
              Período dos gráficos
            </h2>
            <Card>
              <CardContent className="pt-5">
                <PeriodFilter
                  preset={preset}
                  range={range}
                  minDate={bounds.first}
                  maxDate={bounds.last}
                  onPresetChange={handlePreset}
                  onCustomRange={handleCustomRange}
                  invalidRange={invalidRange}
                />
                <p className="mt-3 text-xs text-muted-foreground">
                  O período vale para todos os gráficos abaixo, que compartilham o mesmo eixo de
                  datas: o zoom e o cursor de um gráfico acompanham os demais. Cada indicador
                  mantém a periodicidade em que é publicado (bimestre do RREO ou quadrimestre do
                  RGF) e os valores estão em reais correntes, sem correção pela inflação.
                </p>
              </CardContent>
            </Card>
          </section>
          <StatePanels series={series} domain={domain} />
        </>
      )}
    </div>
  );
}

function Highlights({
  dashboard,
  name,
}: {
  dashboard: ReturnType<typeof useStateDashboard>;
  name: string;
}) {
  if (dashboard.status === "error" && !dashboard.data) {
    return <InlineError message={dashboard.error.message} onRetry={dashboard.retry} />;
  }
  if (!dashboard.data) {
    return (
      <div role="status" aria-live="polite" className="text-sm text-muted-foreground">
        Carregando dados oficiais…
      </div>
    );
  }
  const available = dashboard.data.indicators.filter((i) => i.status === "available");
  if (available.length === 0) {
    return (
      <p className="rounded-lg border border-border p-5 text-sm text-muted-foreground">
        Ainda não há dados fiscais armazenados para {name}. Os indicadores aparecem aqui depois da
        coleta dos relatórios que o estado entrega ao SICONFI; nenhum valor é estimado.
      </p>
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {available.map((item) => (
        <StateIndicatorCard key={item.indicator.code} item={item} />
      ))}
    </div>
  );
}

/** One request loads every series; each panel gets its own slice of that request's state. */
function seriesState(
  resource: ResourceState<StateIndicators> & { retry: () => void },
  item: StateIndicatorSeries,
): ResourceState<StateIndicatorSeries> & { retry: () => void } {
  const { retry } = resource;
  if (resource.status === "error") return { status: "error", data: item, error: resource.error, retry };
  if (resource.status === "loading") return { status: "loading", data: item, retry };
  return { status: "success", data: item, retry };
}

function StatePanels({
  series,
  domain,
}: {
  series: ReturnType<typeof useStateIndicators>;
  domain: { min: string; max: string } | null;
}) {
  if (series.status === "error" && !series.data) {
    return (
      <Card>
        <ErrorState message={series.error.message} onRetry={series.retry} />
      </Card>
    );
  }
  if (!series.data) {
    return (
      <Card>
        <LoadingState />
      </Card>
    );
  }
  return (
    <>
      {series.data.indicators
        .filter((item) => item.status === "available")
        .map((item) => {
          const { indicator } = item;
          const headingId = `chart-${indicator.code}`;
          return (
            <Card key={indicator.code} aria-labelledby={headingId}>
              <CardHeader>
                <h2 id={headingId} className="text-lg font-semibold">
                  {indicator.name}
                </h2>
                <p className="text-sm text-muted-foreground">{indicator.description}</p>
              </CardHeader>
              <CardContent>
                <SeriesBody
                  series={seriesState(series, item)}
                  step={false}
                  domain={domain}
                  resetsEachYear={resetsEachYear(indicator.code)}
                  notes={[item.accumulation_window]}
                />
              </CardContent>
            </Card>
          );
        })}
    </>
  );
}
