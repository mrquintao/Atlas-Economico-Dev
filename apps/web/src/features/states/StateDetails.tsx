"use client";

import Link from "next/link";
import { useId, useRef } from "react";

import { InlineError } from "@/components/ui/states";
import { useStateDashboard } from "@/hooks/useObservations";
import { formatPeriod, formatValue } from "@/lib/format";
import { REGION_NAMES, statePath, STATES, type StateUnit } from "@/lib/states";
import type { StateMap } from "@/types/api";

import type { MapScale } from "./map-scale";
import { Swatch } from "./Swatch";

interface Props {
  /** Selected UF, or null before any selection. */
  uf: StateUnit | null;
  data: StateMap;
  scale: MapScale;
  periodLabel: string;
  onSelect: (acronym: string | null) => void;
}

/**
 * Side panel of the map: the selected UF's value in the map (same indicator and period) and its
 * latest published value of every state indicator. Each value keeps its own reference period:
 * the panel never mixes periods into a single figure.
 */
export function StateDetails({ uf, data, scale, periodLabel, onSelect }: Props) {
  const headingId = useId();
  const pickerId = useId();
  const pickerRef = useRef<HTMLSelectElement>(null);
  const mapItem = uf ? data.states.find((s) => s.geography.acronym === uf.acronym) : undefined;
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-5 rounded-lg border border-border bg-background/60 p-5"
    >
      {/* Announces each new selection: the panel sits after the 27 UFs in the tab order. */}
      <p aria-live="polite" className="sr-only">
        {uf
          ? `${uf.name} selecionada. ${data.indicator.short_name}: ${
              mapItem?.value == null ? "sem dado" : formatValue(mapItem.value, data.indicator.unit)
            }, ${periodLabel}.`
          : ""}
      </p>
      {uf ? (
        <Selected
          uf={uf}
          data={data}
          scale={scale}
          periodLabel={periodLabel}
          headingId={headingId}
          onClear={() => {
            onSelect(null);
            // The clear button unmounts: keep the keyboard focus inside the panel.
            pickerRef.current?.focus();
          }}
        />
      ) : (
        <div className="flex flex-col gap-2">
          <h3 id={headingId} className="text-base font-semibold">
            Nenhuma UF selecionada
          </h3>
          <p className="text-sm text-muted-foreground">
            Clique numa UF do mapa (ou use Tab e Enter) para ver aqui o valor do indicador no
            período e os últimos valores fiscais publicados pela UF.
          </p>
        </div>
      )}
      <label htmlFor={pickerId} className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
        {uf ? "Escolher outra UF" : "Ou escolha na lista"}
        <select
          ref={pickerRef}
          id={pickerId}
          value={uf?.acronym ?? ""}
          onChange={(event) => onSelect(event.target.value || null)}
          className="rounded-md border border-border-strong bg-card px-2 py-1.5 text-sm text-foreground"
        >
          <option value="">Selecione uma UF</option>
          {STATES.toSorted((a, b) => a.name.localeCompare(b.name, "pt-BR")).map((state) => (
            <option key={state.acronym} value={state.acronym}>
              {state.name}
            </option>
          ))}
        </select>
      </label>
    </section>
  );
}

function Selected({
  uf,
  data,
  scale,
  periodLabel,
  headingId,
  onClear,
}: Omit<Props, "uf" | "onSelect"> & { uf: StateUnit; headingId: string; onClear: () => void }) {
  const { indicator } = data;
  const item = data.states.find((s) => s.geography.acronym === uf.acronym);
  const value = item?.value ?? null;
  const index = scale.classify(value);
  return (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">
            Região {REGION_NAMES[uf.region]}
          </p>
          <h3 id={headingId} className="text-xl font-semibold tracking-tight">
            {uf.name}
            {uf.acronym === "DF" ? "*" : ""} <span className="font-normal text-muted-foreground">{uf.acronym}</span>
          </h3>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          Limpar seleção
        </button>
      </div>

      <div className="flex flex-col gap-1 border-t border-border pt-4">
        <p className="text-xs font-medium text-muted-foreground">
          {indicator.short_name} · {periodLabel}
        </p>
        {value === null ? (
          <>
            <p className="text-2xl font-semibold text-muted-foreground">Sem dado</p>
            <p className="text-xs text-muted-foreground">
              Nenhum valor publicado neste período. Ausência não é zero.
            </p>
          </>
        ) : (
          <>
            <p className="text-3xl font-semibold tabular-nums tracking-tight">{formatValue(value, indicator.unit)}</p>
            <p className="text-xs text-muted-foreground">{data.accumulation_window}</p>
            {index !== null && (
              <p className="flex items-center gap-2 text-xs text-muted-foreground">
                <Swatch color={scale.classes[index].color} />
                Faixa {index + 1} de {scale.classes.length} da legenda
              </p>
            )}
          </>
        )}
      </div>

      <LatestValues uf={uf.acronym} key={uf.acronym} />

      <Link
        href={statePath(uf)}
        className="inline-flex items-center justify-center rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        Abrir o painel completo da UF
      </Link>
    </>
  );
}

/** Latest published value of each state indicator of the UF, in its own reference period. */
export function LatestValues({ uf }: { uf: string }) {
  const dashboard = useStateDashboard(uf);
  const titleId = useId();

  let body;
  if (dashboard.status === "error" && !dashboard.data) {
    body = <InlineError message={dashboard.error.message} onRetry={dashboard.retry} />;
  } else if (!dashboard.data) {
    body = (
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
        Carregando dados oficiais…
      </p>
    );
  } else {
    const available = dashboard.data.indicators.filter((i) => i.latest !== null);
    const missing = dashboard.data.indicators.filter((i) => i.latest === null);
    body = (
      <>
        {available.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Ainda não há dados fiscais armazenados para esta UF. Nenhum valor é estimado.
          </p>
        ) : (
          <dl className="flex flex-col divide-y divide-border">
            {available.map(({ indicator, latest, accumulation_window }) => (
              <div key={indicator.code} className="flex items-baseline justify-between gap-4 py-2">
                <dt className="text-sm">
                  {indicator.short_name}
                  <span className="block text-xs text-muted-foreground">
                    {latest && formatPeriod(indicator.frequency, latest.period_start, true)}
                  </span>
                  <span className="block text-xs text-muted-foreground">{accumulation_window}</span>
                </dt>
                <dd className="shrink-0 text-right text-sm font-medium tabular-nums">
                  {latest && formatValue(latest.value, indicator.unit)}
                </dd>
              </div>
            ))}
          </dl>
        )}
        {available.length > 0 && missing.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Sem dados nesta UF: {missing.map((i) => i.indicator.short_name).join(", ")}.
          </p>
        )}
        {dashboard.data.notes.map((note) => (
          <p key={note} className="border-l-2 border-amber-500 pl-3 text-xs text-amber-950">
            * {note}
          </p>
        ))}
      </>
    );
  }

  return (
    <div role="region" aria-labelledby={titleId} className="flex flex-col gap-2 border-t border-border pt-4">
      <h4 id={titleId} className="text-sm font-semibold">
        Últimos valores publicados
      </h4>
      {body}
      <p className="text-xs text-muted-foreground">
        Cada valor está no seu próprio período de referência. Valores em reais estão em reais correntes, sem correção pela inflação.
      </p>
    </div>
  );
}
