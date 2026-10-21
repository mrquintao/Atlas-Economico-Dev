"use client";

import { useMemo, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { InlineError } from "@/components/ui/states";
import { useIndicators } from "@/hooks/useObservations";
import {
  DEFAULT_PRESET,
  isValidRange,
  rangeForPreset,
  SINCE_2008_START,
  startOfMonth,
  todayLocalIso,
  type DateRange,
  type PeriodPreset,
} from "@/lib/period";
import type { Indicator } from "@/types/api";

import { IndicatorHighlight } from "./IndicatorHighlight";
import { IndicatorPanel } from "./IndicatorPanel";
import { DASHBOARD_INDICATORS } from "./indicators";
import { PeriodFilter } from "./PeriodFilter";

interface StoredBounds {
  first: string | null;
  last: string | null;
}

/** Earliest first and latest last stored date across the dashboard's indicators. */
export function storedBounds(indicators: Indicator[]): StoredBounds {
  const codes = new Set(DASHBOARD_INDICATORS.map((i) => i.code));
  const shown = indicators.filter((i) => codes.has(i.code));
  const firsts = shown.flatMap((i) => (i.first_stored_date ? [i.first_stored_date] : []));
  const lasts = shown.flatMap((i) => (i.last_stored_date ? [i.last_stored_date] : []));
  return {
    first: firsts.length ? firsts.reduce((a, b) => (a < b ? a : b)) : null,
    last: lasts.length ? lasts.reduce((a, b) => (a > b ? a : b)) : null,
  };
}

export function Dashboard() {
  // One shared range for every chart on the page (charts are time-synchronised).
  const [preset, setPreset] = useState<PeriodPreset>(DEFAULT_PRESET);
  const [range, setRange] = useState<DateRange>({ start: SINCE_2008_START, end: null });
  const invalidRange = !isValidRange(range);
  // An invalid range is never sent to the API; the last valid one stays displayed.
  const [appliedRange, setAppliedRange] = useState<DateRange>(range);

  const catalog = useIndicators();
  const byCode = useMemo(
    () => new Map((catalog.data ?? []).map((i) => [i.code, i])),
    [catalog.data],
  );
  const bounds = useMemo(() => storedBounds(catalog.data ?? []), [catalog.data]);

  // Same x-axis for every chart, so the same date sits at the same horizontal position. It
  // starts on the 1st of the month: monthly points (dated on the 1st) of a month that overlaps
  // the range are included by the API and must be visible.
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
    // Relative presets ("5 anos") end at the latest official observation of any indicator.
    updateRange(rangeForPreset(next, bounds.last ?? todayLocalIso()));
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
          {DASHBOARD_INDICATORS.map((config) => (
            <IndicatorHighlight key={config.code} config={config} />
          ))}
        </div>
      </section>

      <section aria-labelledby="period" className="flex flex-col gap-3">
        <h2 id="period" className="sr-only">
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
            {catalog.status === "error" && (
              <div className="mt-3">
                <InlineError
                  message={`Não foi possível carregar o catálogo de indicadores: ${catalog.error.message} Sem ele, os gráficos podem não ficar alinhados no mesmo eixo de datas.`}
                  onRetry={catalog.retry}
                />
              </div>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              O período vale para todos os gráficos abaixo, que compartilham o mesmo eixo de datas:
              o zoom e o cursor de um gráfico acompanham os demais. Cada indicador mantém sua
              frequência e unidade originais. Use a roda do mouse, o gesto de pinça ou a barra
              inferior de cada gráfico para ampliar.
            </p>
          </CardContent>
        </Card>
      </section>

      {DASHBOARD_INDICATORS.map((config) => (
        <IndicatorPanel
          key={config.code}
          config={config}
          indicator={byCode.get(config.code) ?? null}
          range={appliedRange}
          domain={domain}
        />
      ))}
    </div>
  );
}
