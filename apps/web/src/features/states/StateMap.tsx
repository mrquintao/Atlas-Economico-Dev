"use client";

import Link from "next/link";
import { useId, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { InlineError, LoadingState, RefreshingIndicator, RetryButton } from "@/components/ui/states";
import { useIndicators, useStateBoundaries, useStateMap } from "@/hooks/useObservations";
import { formatPeriod, formatValue } from "@/lib/format";
import { findState, statePath } from "@/lib/states";
import type { Indicator, StateBoundaries, StateMap, StateMapValue } from "@/types/api";

import { projectShapes } from "./map-geometry";
import { buildScale, NO_DATA_FILL, type MapScale } from "./map-scale";
import { keptPeriod, STATE_INDICATOR_ORDER } from "./state-indicators";
import { StateDetails } from "./StateDetails";
import { Swatch } from "./Swatch";

/** A ratio published since 2018 and never negative (economist, S6). */
export const DEFAULT_MAP_CODE = "STATE_PERSONNEL_EXEC_RCL";

const WIDTH = 640;
const HEIGHT = 600;
const TOTAL_UFS = 27;

export const NO_DATA_LABEL =
  "Sem dado: a UF não entregou o relatório ao SICONFI ou a linha não foi publicada. Ausência não é zero.";
export const QUANTILE_NOTE =
  "Classes por quantis do período selecionado: cada faixa reúne um número semelhante de UFs. As " +
  "faixas mudam de um período para outro; cores de períodos diferentes não são comparáveis.";
export const DIVERGING_NOTE =
  "Zero separa as cores: valores negativos indicam déficit (resultados) ou haveres financeiros " +
  "maiores que a dívida (DCL).";
const SOURCE_NOTE = "Fonte: Tesouro Nacional, SICONFI (RREO e RGF), valores como publicados.";

/** Name of a UF as shown next to the map: the DF carries the comparability asterisk. */
export function displayName(geography: { acronym: string; name: string }): string {
  return geography.acronym === "DF" ? `${geography.name}*` : geography.name;
}

export function valueLabel(item: StateMapValue, unit: string): string {
  return item.value === null ? "sem dado" : formatValue(item.value, unit);
}

/**
 * Choropleth of one state indicator in the 27 UFs, with a period filter and a table. A click (or
 * Enter) on a UF selects it and shows its values in the side panel; the panel links to the
 * UF's page.
 */
export function StateMapPanel() {
  const [code, setCode] = useState(DEFAULT_MAP_CODE);
  // The selection survives indicator and period changes.
  const [selected, setSelected] = useState<string | null>(null);
  // null: the API's default period (the most recent well-covered one).
  const [referenceDate, setReferenceDate] = useState<string | null>(null);
  const catalog = useIndicators();
  const map = useStateMap(code, referenceDate);
  const boundaries = useStateBoundaries();

  const options = useMemo(() => stateIndicatorOptions(catalog.data ?? []), [catalog.data]);

  function handleIndicator(next: string) {
    // The period shown belongs to the indicator of the data on screen, not to the last choice.
    const current = options.find((i) => i.code === map.data?.indicator.code);
    const target = options.find((i) => i.code === next);
    setCode(next);
    setReferenceDate(keptPeriod(map.data?.period?.reference_date ?? null, current, target));
  }

  const headingId = useId();
  const indicatorId = useId();
  const periodId = useId();
  // After a failed request the previous data stays in the resource; never show another
  // indicator's map under the error.
  const data = map.status === "error" && map.data?.indicator.code !== code ? null : map.data;
  const periodNotFound = map.status === "error" && map.error.code === "period_not_found";

  return (
    <Card aria-labelledby={headingId}>
      <CardHeader>
        <h2 id={headingId} className="text-lg font-semibold">
          Mapa das UFs
        </h2>
        <p className="text-sm text-muted-foreground">
          Escolha um indicador e um período; todas as UFs aparecem no mesmo período. Clique numa UF
          (ou use Tab e Enter) para ver os dados dela ao lado do mapa.
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
              className="rounded-md border border-border-strong bg-card px-2 py-1.5 text-sm text-foreground"
            >
              {(options.length ? options : [{ code, short_name: data?.indicator.short_name ?? code }]).map(
                (option) => (
                  <option key={option.code} value={option.code}>
                    {option.short_name}
                  </option>
                ),
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
              className="rounded-md border border-border-strong bg-card px-2 py-1.5 text-sm text-foreground disabled:opacity-60"
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
          {map.status === "loading" && data && <RefreshingIndicator />}
        </div>

        {periodNotFound ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 text-sm">
            <span>{map.error.message}</span>
            <button
              type="button"
              onClick={() => setReferenceDate(null)}
              className="rounded-md border border-border px-2.5 py-1 font-medium hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
            >
              Ver o período padrão
            </button>
          </div>
        ) : map.status === "error" ? (
          <InlineError message={map.error.message} onRetry={map.retry} />
        ) : null}

        {!data ? (
          map.status !== "error" && <LoadingState />
        ) : (
          <MapBody data={data} boundaries={boundaries} selected={selected} onSelect={setSelected} />
        )}
      </CardContent>
    </Card>
  );
}

type OptionIndicator = Pick<Indicator, "code" | "short_name" | "frequency" | "first_stored_date" | "last_stored_date">;

/** The state indicators of the catalog, in the display order of the state pages. */
export function stateIndicatorOptions(indicators: readonly Indicator[]): OptionIndicator[] {
  return STATE_INDICATOR_ORDER.flatMap((code) => indicators.filter((i) => i.code === code));
}

function MapBody({
  data,
  boundaries,
  selected,
  onSelect,
}: {
  data: StateMap;
  boundaries: ReturnType<typeof useStateBoundaries>;
  selected: string | null;
  onSelect: (acronym: string | null) => void;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const scale = useMemo(() => buildScale(data.scale, data.states.map((s) => s.value)), [data]);
  const { indicator, period } = data;
  const periodLabel = period ? formatPeriod(indicator.frequency, period.reference_date, true) : null;
  const covered = data.states.filter((s) => s.status === "available").length;

  if (!period) {
    return (
      <p className="rounded-lg border border-border p-5 text-sm text-muted-foreground">
        Ainda não há valores de {indicator.short_name} armazenados para nenhuma UF. Nenhum valor é
        estimado.
      </p>
    );
  }

  return (
    <>
      <p className="text-sm">
        <strong>{indicator.name}</strong> — {periodLabel}. {data.accumulation_window}{" "}
        <span className="text-muted-foreground">
          {covered} de {TOTAL_UFS} UFs com dado publicado neste período.
        </span>
      </p>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          {boundaries.data ? (
            <ChoroplethSvg
              data={data}
              boundaries={boundaries.data}
              scale={scale}
              periodLabel={periodLabel ?? ""}
              selected={selected}
              onSelect={(acronym, viaPointer) => {
                onSelect(acronym);
                // Small screens: the panel sits below the map; bring it into view after a tap.
                // Keyboard selections keep the page still, so focus and viewport stay together.
                if (acronym && viaPointer && window.matchMedia?.("(max-width: 1023px)").matches) {
                  panelRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
                }
              }}
            />
          ) : boundaries.status === "error" ? (
            <div className="flex flex-col gap-2 rounded-lg border border-border p-5 text-sm">
              <p>
                {boundaries.error.code === "boundaries_not_found"
                  ? "A malha oficial das UFs (IBGE) ainda não foi coletada; os valores estão na tabela."
                  : boundaries.error.message}
              </p>
              <div>
                <RetryButton onRetry={boundaries.retry} />
              </div>
            </div>
          ) : (
            <LoadingState label="Carregando a malha das UFs…" />
          )}
          <Legend data={data} scale={scale} />
        </div>
        <div ref={panelRef} className="scroll-mt-4 lg:sticky lg:top-4">
          <StateDetails
            uf={selected ? findState(selected) : null}
            data={data}
            scale={scale}
            periodLabel={periodLabel ?? ""}
            onSelect={onSelect}
          />
        </div>
      </div>
      <MapNotes data={data} />
      <MapTable data={data} scale={scale} periodLabel={periodLabel ?? ""} />
      <p className="text-xs text-muted-foreground">
        {SOURCE_NOTE}
        {boundaries.data ? ` Malha: IBGE, edição ${boundaries.data.metadata.mesh_year}.` : ""}{" "}
        {data.default_rule}
      </p>
    </>
  );
}

interface Hovered {
  acronym: string;
  x: number;
  y: number;
}

function ChoroplethSvg({
  data,
  boundaries,
  scale,
  periodLabel,
  selected,
  onSelect,
}: {
  data: StateMap;
  boundaries: StateBoundaries;
  scale: MapScale;
  periodLabel: string;
  selected: string | null;
  onSelect: (acronym: string | null, viaPointer?: boolean) => void;
}) {
  // Pointer and keyboard are tracked apart: the pointer leaving the map never hides the focus.
  const [hovered, setHovered] = useState<Hovered | null>(null);
  const [focused, setFocused] = useState<Hovered | null>(null);
  const patternId = `no-data-${useId().replace(/:/g, "")}`;
  const { unit } = data.indicator;
  const byAcronym = useMemo(() => new Map(data.states.map((s) => [s.geography.acronym, s])), [data.states]);

  // The official meshes follow RFC 7946; projectShapes rewinds them for d3.
  const shapes = useMemo(() => projectShapes(boundaries, WIDTH, HEIGHT), [boundaries]);

  function fill(acronym: string): string {
    const item = byAcronym.get(acronym);
    const index = scale.classify(item?.value ?? null);
    return index === null ? `url(#${patternId})` : scale.classes[index].color;
  }

  function toggle(acronym: string, viaPointer = false) {
    onSelect(selected === acronym ? null : acronym, viaPointer);
  }

  function handleKey(event: KeyboardEvent<Element>, acronym: string) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      toggle(acronym);
    } else if (event.key === "Escape") {
      onSelect(null);
    }
  }

  function track(event: MouseEvent<Element>, acronym: string) {
    const box = event.currentTarget.closest("svg")?.getBoundingClientRect();
    if (!box) return;
    setHovered({
      acronym,
      x: ((event.clientX - box.left) / box.width) * WIDTH,
      y: ((event.clientY - box.top) / box.height) * HEIGHT,
    });
  }

  const active = hovered ?? focused;
  const hoveredShape = hovered ? shapes.find((s) => s.acronym === hovered.acronym) : undefined;
  const focusedShape = focused ? shapes.find((s) => s.acronym === focused.acronym) : undefined;
  const selectedShape = selected ? shapes.find((s) => s.acronym === selected) : undefined;
  const activeItem = active ? byAcronym.get(active.acronym) : undefined;
  const df = shapes.find((s) => s.acronym === "DF");

  return (
    <div className="relative">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-auto w-full"
        role="group"
        aria-label={`Mapa de ${data.indicator.short_name} por UF, ${periodLabel}`}
        onMouseLeave={() => setHovered(null)}
        data-selected={selected ?? undefined}
      >
        <defs>
          <pattern id={patternId} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="6" height="6" fill={NO_DATA_FILL} />
            <line x1="0" y1="0" x2="0" y2="6" stroke="#6b7280" strokeWidth="1.5" />
          </pattern>
        </defs>
        {shapes.map((shape) => {
          const item = byAcronym.get(shape.acronym);
          const label = `${item ? displayName(item.geography) : shape.name}: ${
            item ? valueLabel(item, unit) : "sem dado"
          }, ${periodLabel}`;
          return (
            // A toggle button per UF: focusable with Tab; a click, Enter or Space selects it.
            <path
              key={shape.acronym}
              role="button"
              tabIndex={0}
              aria-label={label}
              aria-pressed={selected === shape.acronym}
              data-uf={shape.acronym}
              d={shape.d}
              fill={fill(shape.acronym)}
              stroke="#ffffff"
              strokeWidth={0.8}
              strokeLinejoin="round"
              onClick={() => toggle(shape.acronym, true)}
              onKeyDown={(event) => handleKey(event, shape.acronym)}
              onMouseMove={(event) => track(event, shape.acronym)}
              onFocus={(event) => {
                // Only keyboard focus gets the ring and tooltip; a mouse click also focuses.
                if (!event.currentTarget.matches(":focus-visible")) return;
                setFocused({ acronym: shape.acronym, x: shape.centroid[0], y: shape.centroid[1] });
              }}
              onBlur={() => setFocused(null)}
              className="cursor-pointer outline-none transition-[filter] hover:brightness-110"
            />
          );
        })}
        {df && (
          <text
            x={df.centroid[0] + 6}
            y={df.centroid[1] - 4}
            fontSize="16"
            fontWeight="700"
            fill="var(--foreground)"
            stroke="var(--background)"
            strokeWidth="3"
            paintOrder="stroke"
            pointerEvents="none"
            aria-hidden
          >
            *
          </text>
        )}
        {/* Outlines are a white halo under a dark stroke: visible on every class colour. */}
        {hoveredShape && hoveredShape !== selectedShape && (
          <g pointerEvents="none" aria-hidden>
            <path d={hoveredShape.d} fill="none" stroke="#ffffff" strokeWidth={3.5} strokeLinejoin="round" />
            <path d={hoveredShape.d} fill="none" stroke="var(--foreground)" strokeWidth={1.5} strokeLinejoin="round" />
          </g>
        )}
        {selectedShape && (
          <g pointerEvents="none" aria-hidden>
            <path d={selectedShape.d} fill="none" stroke="#ffffff" strokeWidth={5} strokeLinejoin="round" />
            <path d={selectedShape.d} fill="none" stroke="var(--foreground)" strokeWidth={2.5} strokeLinejoin="round" />
          </g>
        )}
        {focusedShape && (
          // Keyboard focus: dashed accent ring, drawn last and distinct from the selection.
          <g pointerEvents="none" aria-hidden data-focus-ring={focusedShape.acronym}>
            <path d={focusedShape.d} fill="none" stroke="#ffffff" strokeWidth={6} strokeLinejoin="round" />
            <path
              d={focusedShape.d}
              fill="none"
              stroke="var(--accent)"
              strokeWidth={2.5}
              strokeDasharray="6 3"
              strokeLinejoin="round"
            />
          </g>
        )}
      </svg>
      {active && activeItem && (
        <div
          role="tooltip"
          className="pointer-events-none absolute z-10 w-max max-w-60 -translate-x-1/2 -translate-y-full rounded-md border border-border bg-card px-3 py-2 text-xs shadow-md"
          style={{
            left: `${(active.x / WIDTH) * 100}%`,
            top: `calc(${(active.y / HEIGHT) * 100}% - 8px)`,
          }}
        >
          <p className="font-semibold">{displayName(activeItem.geography)}</p>
          <p>{valueLabel(activeItem, unit)}</p>
          <p className="text-muted-foreground">
            {activeItem.value === null ? NO_DATA_SHORT : unit} · {periodLabel}
          </p>
        </div>
      )}
    </div>
  );
}

const NO_DATA_SHORT = "nenhum valor publicado (não é zero)";

function Legend({ data, scale }: { data: StateMap; scale: MapScale }) {
  const { unit } = data.indicator;
  const missing = data.states.filter((s) => s.status === "no_data").length;
  return (
    <div className="flex flex-col gap-2 text-sm">
      <h3 className="text-xs font-semibold text-muted-foreground">Legenda ({unit})</h3>
      <ul aria-label="Legenda do mapa" className="flex flex-wrap gap-x-5 gap-y-1.5">
        {scale.classes.map((c) => (
          <li key={`${c.min}-${c.max}`} className="flex items-center gap-2">
            <Swatch color={c.color} />
            <span className="tabular-nums">
              {c.min === c.max ? formatValue(c.min, unit) : `${formatValue(c.min, unit)} a ${formatValue(c.max, unit)}`}{" "}
              <span className="text-muted-foreground">
                ({c.count} {c.count === 1 ? "UF" : "UFs"})
              </span>
            </span>
          </li>
        ))}
        <li className="flex items-center gap-2">
          <Swatch hatched />
          <span>
            Sem dado{" "}
            <span className="text-muted-foreground">
              ({missing} {missing === 1 ? "UF" : "UFs"})
            </span>
          </span>
        </li>
      </ul>
    </div>
  );
}

/** How to read the colours, absences and the UFs' comparability notes. */
function MapNotes({ data }: { data: StateMap }) {
  return (
    <div className="flex max-w-4xl flex-col gap-1.5 text-xs text-muted-foreground">
      <p>{QUANTILE_NOTE}</p>
      {data.scale === "diverging" && <p>{DIVERGING_NOTE}</p>}
      <p>{NO_DATA_LABEL}</p>
      {data.notes.map((note) => (
        <p key={note}>{note.startsWith("O Distrito Federal") ? `* ${note}` : note}</p>
      ))}
    </div>
  );
}

function MapTable({ data, scale, periodLabel }: { data: StateMap; scale: MapScale; periodLabel: string }) {
  const { unit } = data.indicator;
  const rows = data.states.toSorted((a, b) => a.geography.name.localeCompare(b.geography.name, "pt-BR"));
  return (
    <details className="text-sm">
      <summary className="cursor-pointer font-medium">Ver os valores em tabela</summary>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <caption className="sr-only">
            {data.indicator.name} por UF, {periodLabel}
          </caption>
          <thead>
            <tr className="border-b border-border text-xs text-muted-foreground">
              <th scope="col" className="py-1.5 pr-4 font-medium">
                UF
              </th>
              <th scope="col" className="py-1.5 pr-4 font-medium">
                Valor ({unit})
              </th>
              <th scope="col" className="py-1.5 font-medium">
                Faixa da legenda
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => {
              const index = scale.classify(item.value);
              return (
                <tr key={item.geography.acronym} className="border-b border-border/60">
                  <th scope="row" className="py-1.5 pr-4 font-normal">
                    <Link href={statePath(item.geography)} className="underline-offset-4 hover:underline">
                      {displayName(item.geography)} ({item.geography.acronym})
                    </Link>
                  </th>
                  <td className="py-1.5 pr-4 tabular-nums">{valueLabel(item, unit)}</td>
                  <td className="py-1.5">
                    <span className="inline-flex items-center gap-2">
                      <Swatch hatched={index === null} color={index === null ? undefined : scale.classes[index].color} />
                      {index === null ? "Sem dado" : `${index + 1}ª de ${scale.classes.length}`}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
