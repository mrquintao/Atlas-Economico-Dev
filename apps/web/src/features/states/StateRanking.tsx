"use client";

import Link from "next/link";
import { useId, useMemo, useState } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Segmented } from "@/components/ui/segmented";
import { InlineError, LoadingState, RefreshingIndicator } from "@/components/ui/states";
import { useIndicators, useStateRanking } from "@/hooks/useObservations";
import { formatPeriod, formatValue } from "@/lib/format";
import { statePath, STATES } from "@/lib/states";
import type { RankingOrder, StateRanking } from "@/types/api";

import { barGeometry } from "./ranking-bars";
import { keptPeriod } from "./state-indicators";
import { displayName, stateIndicatorOptions } from "./StateMap";
import { UfPicker } from "./UfPicker";

/** The issue's example of a relative metric; comparable across UFs of different sizes. */
export const DEFAULT_RANKING_CODE = "STATE_DCL_RCL";
/** Published ratios (percent of the RCL): preferred for rankings (economist, S8). */
export const RELATIVE_CODES: readonly string[] = ["STATE_DCL_RCL", "STATE_PERSONNEL_EXEC_RCL"];
export const MIN_RANKING_UFS = 2;
const ALL_UFS = STATES.map((s) => s.acronym).toSorted();

const ORDER_OPTIONS: { value: RankingOrder; label: string }[] = [
  { value: "desc", label: "Maior → menor" },
  { value: "asc", label: "Menor → maior" },
];

/** Ranking of UFs by one state indicator at a single period, relative metrics first. */
export function StateRankingPanel() {
  const [code, setCode] = useState(DEFAULT_RANKING_CODE);
  const [referenceDate, setReferenceDate] = useState<string | null>(null);
  const [order, setOrder] = useState<RankingOrder>("desc");
  const [selected, setSelected] = useState<string[]>(ALL_UFS);
  // A selection with fewer than two UFs is never sent: the last valid one stays applied.
  const [applied, setApplied] = useState<string[]>(ALL_UFS);
  const catalog = useIndicators();
  const ufs = applied.length === ALL_UFS.length ? null : applied;
  const ranking = useStateRanking(code, referenceDate, ufs, order);

  const options = useMemo(() => stateIndicatorOptions(catalog.data ?? []), [catalog.data]);
  const relative = options.filter((o) => RELATIVE_CODES.includes(o.code));
  const absolute = options.filter((o) => !RELATIVE_CODES.includes(o.code));

  function handleIndicator(next: string) {
    const current = options.find((i) => i.code === ranking.data?.indicator.code);
    const target = options.find((i) => i.code === next);
    setCode(next);
    setReferenceDate(keptPeriod(ranking.data?.period?.reference_date ?? null, current, target));
  }

  function handleSelection(next: string[]) {
    const sorted = next.toSorted();
    setSelected(sorted);
    if (sorted.length >= MIN_RANKING_UFS) setApplied(sorted);
  }

  const headingId = useId();
  const indicatorId = useId();
  const periodId = useId();
  const data = ranking.status === "error" && ranking.data?.indicator.code !== code ? null : ranking.data;
  const periodNotFound = ranking.status === "error" && ranking.error.code === "period_not_found";

  return (
    <Card aria-labelledby={headingId}>
      <CardHeader>
        <h2 id={headingId} className="text-lg font-semibold">
          Ranking das UFs
        </h2>
        <p className="text-sm text-muted-foreground">
          Ordena as UFs selecionadas pelo valor publicado num mesmo período. Para comparar UFs de
          portes diferentes, prefira as métricas relativas (percentuais da receita corrente
          líquida).
        </p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end gap-4">
          <label htmlFor={indicatorId} className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
            Indicador
            <select
              id={indicatorId}
              value={code}
              onChange={(event) => handleIndicator(event.target.value)}
              className="rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground"
            >
              {options.length ? (
                <>
                  <optgroup label="Métricas relativas (recomendadas)">
                    {relative.map((o) => (
                      <option key={o.code} value={o.code}>
                        {o.short_name}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="Valores absolutos (refletem o porte da UF)">
                    {absolute.map((o) => (
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
          <label htmlFor={periodId} className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
            Período
            <select
              id={periodId}
              value={data?.period?.reference_date ?? ""}
              disabled={!data || data.available_periods.length === 0}
              onChange={(event) => setReferenceDate(event.target.value)}
              className="rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground disabled:opacity-60"
            >
              {data?.available_periods.length ? (
                data.available_periods.map((period) => (
                  <option key={period.reference_date} value={period.reference_date}>
                    {formatPeriod(data.indicator.frequency, period.reference_date, true)} — {period.coverage}{" "}
                    {period.coverage === 1 ? "UF" : "UFs"}
                  </option>
                ))
              ) : (
                <option value="">Sem períodos</option>
              )}
            </select>
          </label>
          <div className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
            Ordem
            <Segmented label="Ordem do ranking" options={ORDER_OPTIONS} value={order} onChange={setOrder} />
          </div>
          {ranking.status === "loading" && data && <RefreshingIndicator />}
        </div>
        <details className="text-sm">
          <summary className="cursor-pointer font-medium">
            UFs selecionadas ({selected.length} de {ALL_UFS.length})
          </summary>
          <div className="mt-3">
            <UfPicker legend="UFs no ranking" selected={selected} onChange={handleSelection} bulk />
          </div>
        </details>
        {selected.length < MIN_RANKING_UFS && (
          <p role="alert" className="text-sm">
            Selecione ao menos {MIN_RANKING_UFS} UFs. O ranking abaixo mantém a seleção anterior (
            {applied.length} UFs).
          </p>
        )}

        {periodNotFound ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 text-sm">
            <span>{ranking.error.message}</span>
            <button
              type="button"
              onClick={() => setReferenceDate(null)}
              className="rounded-md border border-border px-2.5 py-1 font-medium hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
            >
              Ver o período padrão
            </button>
          </div>
        ) : ranking.status === "error" ? (
          <InlineError message={ranking.error.message} onRetry={ranking.retry} />
        ) : null}

        {!data ? ranking.status !== "error" && <LoadingState /> : <RankingBody data={data} />}
      </CardContent>
    </Card>
  );
}

function RankingBody({ data }: { data: StateRanking }) {
  const { indicator, period } = data;
  const geometry = useMemo(() => barGeometry(data.ranking.map((r) => r.value)), [data.ranking]);
  if (!period) {
    return (
      <p className="rounded-lg border border-border p-5 text-sm text-muted-foreground">
        Ainda não há valores de {indicator.short_name} armazenados para nenhuma UF. Nenhum valor é
        estimado.
      </p>
    );
  }
  const periodLabel = formatPeriod(indicator.frequency, period.reference_date, true);
  const { unit } = indicator;
  return (
    <>
      <p className="text-sm">
        <strong>{indicator.name}</strong> — {periodLabel}. {data.accumulation_window}{" "}
        <span className="text-muted-foreground">
          {data.ranked_count} de {data.selected_count} UFs selecionadas com dado publicado neste
          período.
        </span>
      </p>
      {data.metric_kind === "absolute" && (
        <p role="note" className="rounded-lg border border-border bg-muted p-3 text-sm">
          Valor absoluto: a ordem reflete sobretudo o tamanho de cada UF.
        </p>
      )}
      <p className="text-xs text-muted-foreground">{data.order_note}</p>
      {data.ranking.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <caption className="sr-only">
              Ranking de {indicator.name} por UF, {periodLabel} ({unit})
            </caption>
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th scope="col" className="w-16 py-1.5 pr-3 font-medium">
                  Posição
                </th>
                <th scope="col" className="py-1.5 pr-3 font-medium">
                  UF
                </th>
                <th scope="col" className="py-1.5 pr-3 text-right font-medium">
                  Valor ({unit})
                </th>
                <th scope="col" className="hidden w-2/5 py-1.5 font-medium sm:table-cell">
                  <span className="sr-only">Barra proporcional ao valor</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.ranking.map((item, index) => {
                const bar = geometry.bars[index];
                return (
                  <tr key={item.geography.acronym} className="border-b border-border/60" data-uf={item.geography.acronym}>
                    <td className="py-1.5 pr-3 tabular-nums">{item.position}º</td>
                    <th scope="row" className="py-1.5 pr-3 font-normal">
                      <Link href={statePath(item.geography)} className="underline-offset-4 hover:underline">
                        {displayName(item.geography)} ({item.geography.acronym})
                      </Link>
                    </th>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{formatValue(item.value, unit)}</td>
                    <td className="hidden py-1.5 sm:table-cell" aria-hidden>
                      <div className="relative h-3 w-full">
                        {geometry.zero > 0 && (
                          <span className="absolute inset-y-[-2px] w-px bg-muted-foreground" style={{ left: `${geometry.zero}%` }} />
                        )}
                        <span
                          className="absolute inset-y-0 rounded-sm"
                          style={{ left: `${bar.left}%`, width: `${bar.width}%`, backgroundColor: "var(--chart-line)" }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="rounded-lg border border-border p-5 text-sm text-muted-foreground">
          Nenhuma das UFs selecionadas publicou {indicator.short_name} neste período.
        </p>
      )}
      {data.missing_note && (
        <p role="note" className="text-sm">
          {data.missing_note}
        </p>
      )}
      <div className="flex flex-col gap-1.5 text-xs text-muted-foreground">
        {data.notes.map((note) => (
          <p key={note}>{note.startsWith("O Distrito Federal") ? `* ${note}` : note}</p>
        ))}
        <p>
          Fonte: Tesouro Nacional, SICONFI (RREO e RGF), valores como publicados. {data.default_rule}
        </p>
      </div>
    </>
  );
}
