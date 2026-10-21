"use client";

import Link from "next/link";
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent } from "react";

import { LoadingState, RetryButton } from "@/components/ui/states";
import { useStateBoundaries } from "@/hooks/useObservations";
import { findState, REGION_NAMES, statePath, STATES, type StateUnit } from "@/lib/states";

import { projectShapes } from "./map-geometry";
import { LatestValues } from "./StateDetails";

const WIDTH = 600;
const HEIGHT = 580;

interface Pointer {
  acronym: string;
  x: number;
  y: number;
}

/**
 * Geographic map of Brazil to explore the UFs: every UF in the same neutral colour (no data is
 * encoded in the fill), hover shows its name, a click (or Enter) opens its profile beside the
 * map with the latest published fiscal values.
 */
export function StateExplorer() {
  const boundaries = useStateBoundaries();
  const [selected, setSelected] = useState<string | null>(null);
  // Live announcement of the last change (empty until the first one).
  const [announcement, setAnnouncement] = useState("");
  // A region shortcut unmounts on selection: the profile then takes the keyboard focus.
  const [focusProfile, setFocusProfile] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const pickerRef = useRef<HTMLSelectElement>(null);
  const headingId = useId();
  const pickerId = useId();
  const uf = selected ? findState(selected) : null;
  const shapes = useMemo(
    () => (boundaries.data ? projectShapes(boundaries.data, WIDTH, HEIGHT, 4) : null),
    [boundaries.data],
  );

  function select(acronym: string | null, viaPointer = false, fromShortcut = false) {
    setSelected(acronym);
    setFocusProfile(fromShortcut);
    const state = acronym ? findState(acronym) : null;
    setAnnouncement(state ? `UF selecionada: ${state.name}.` : "Seleção limpa.");
    // Small screens: the profile sits below the map; bring it into view after a tap.
    if (acronym && viaPointer && window.matchMedia?.("(max-width: 1023px)").matches) {
      panelRef.current?.scrollIntoView?.({ block: "start", behavior: "smooth" });
    }
  }

  return (
    <section
      aria-labelledby={headingId}
      className="grid rounded-xl border border-border bg-card lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]"
    >
      <h2 id={headingId} className="sr-only">
        Mapa do Brasil
      </h2>
      {/* No overflow clipping on the section: it would break the sticky map and cut tooltips. */}
      <div className="relative rounded-t-xl bg-[#eef2f7] p-4 sm:p-8 lg:rounded-tr-none lg:rounded-l-xl">
        {shapes ? (
          <BrazilMap
            shapes={shapes}
            selected={selected}
            onSelect={select}
          />
        ) : boundaries.status === "error" ? (
          <div className="flex min-h-80 flex-col items-center justify-center gap-3 text-center text-sm">
            <p className="max-w-sm">
              {boundaries.error.code === "boundaries_not_found"
                ? "A malha oficial das UFs (IBGE) ainda não foi coletada. Escolha a UF na lista de UFs."
                : boundaries.error.message}
            </p>
            <RetryButton onRetry={boundaries.retry} />
          </div>
        ) : (
          <LoadingState label="Carregando o mapa do Brasil…" />
        )}
        {shapes && !uf && (
          <p
            aria-hidden
            className="pointer-events-none absolute right-6 bottom-6 flex flex-col items-center gap-1.5 text-sm font-medium text-[#2c3e5a] sm:right-10 sm:bottom-10"
          >
            <ExploreIcon />
            Explore o mapa
          </p>
        )}
      </div>

      <div ref={panelRef} className="flex scroll-mt-4 flex-col gap-5 border-t border-border p-5 sm:p-6 lg:border-t-0 lg:border-l">
        <p aria-live="polite" className="sr-only">
          {announcement}
        </p>
        {uf ? (
          <Profile
            uf={uf}
            autoFocus={focusProfile}
            onClear={() => {
              select(null);
              // The clear button unmounts: keep the keyboard focus inside the panel.
              pickerRef.current?.focus();
            }}
          />
        ) : (
          <div className="flex flex-col gap-2">
            <h3 className="text-xl font-semibold tracking-tight">Explore o mapa</h3>
            <p className="text-sm text-muted-foreground">
              Passe o cursor sobre o mapa e clique numa UF (ou use Tab e Enter) para ver a região
              e os últimos valores fiscais que ela publicou no SICONFI.
            </p>
            <RegionShortcuts onSelect={(acronym) => select(acronym, false, true)} />
          </div>
        )}
        <label htmlFor={pickerId} className="mt-auto flex flex-col gap-1 text-xs font-medium text-muted-foreground">
          {uf ? "Escolher outra UF" : "Ou escolha uma UF"}
          <select
            ref={pickerRef}
            id={pickerId}
            value={uf?.acronym ?? ""}
            onChange={(event) => select(event.target.value || null)}
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
      </div>
    </section>
  );
}

function Profile({ uf, autoFocus, onClear }: { uf: StateUnit; autoFocus: boolean; onClear: () => void }) {
  const titleId = useId();
  const titleRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (autoFocus) titleRef.current?.focus();
  }, [autoFocus, uf.acronym]);
  return (
    <div role="region" aria-labelledby={titleId} className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-accent">
            Região {REGION_NAMES[uf.region]}
          </p>
          <h3 id={titleId} ref={titleRef} tabIndex={-1} className="text-2xl font-semibold tracking-tight outline-none">
            {uf.name} <span className="font-normal text-muted-foreground">{uf.acronym}</span>
          </h3>
          <p className="text-xs text-muted-foreground">Código IBGE {uf.ibgeCode}</p>
        </div>
        <button
          type="button"
          onClick={onClear}
          className="rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          Limpar seleção
        </button>
      </div>
      <LatestValues uf={uf.acronym} key={uf.acronym} />
      <Link
        href={statePath(uf)}
        className="inline-flex items-center justify-center rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        Abrir o painel completo da UF
      </Link>
    </div>
  );
}

function BrazilMap({
  shapes,
  selected,
  onSelect,
}: {
  shapes: ReturnType<typeof projectShapes>;
  selected: string | null;
  onSelect: (acronym: string | null, viaPointer?: boolean) => void;
}) {
  // Pointer and keyboard are tracked apart: the pointer leaving the map never hides the focus.
  const [hovered, setHovered] = useState<Pointer | null>(null);
  const [focused, setFocused] = useState<Pointer | null>(null);
  const byAcronym = useMemo(() => new Map(shapes.map((s) => [s.acronym, s])), [shapes]);

  function toggle(acronym: string, viaPointer = false) {
    onSelect(selected === acronym ? null : acronym, viaPointer);
  }

  function handleKey(event: KeyboardEvent<Element>, shape: { acronym: string; centroid: [number, number] }) {
    const { acronym } = shape;
    // After a click the focus becomes "visible" on the first key press: show the ring then.
    if (focused?.acronym !== acronym && event.currentTarget.matches(":focus-visible")) {
      setFocused({ acronym, x: shape.centroid[0], y: shape.centroid[1] });
    }
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

  const tip = hovered ?? focused;
  const tipShape = tip ? byAcronym.get(tip.acronym) : undefined;
  const selectedShape = selected ? byAcronym.get(selected) : undefined;
  const focusedShape = focused ? byAcronym.get(focused.acronym) : undefined;

  return (
    <div className="relative mx-auto max-w-[640px] lg:sticky lg:top-6">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-auto w-full"
        role="group"
        aria-label="Mapa do Brasil: escolha uma UF"
        onMouseLeave={() => setHovered(null)}
      >
        {shapes.map((shape) => (
          // A toggle button per UF: focusable with Tab; a click, Enter or Space selects it.
          <path
            key={shape.acronym}
            role="button"
            tabIndex={0}
            aria-label={shape.name}
            aria-pressed={selected === shape.acronym}
            data-uf={shape.acronym}
            d={shape.d}
            stroke="#ffffff"
            strokeWidth={1}
            strokeLinejoin="round"
            onClick={() => toggle(shape.acronym, true)}
            onKeyDown={(event) => handleKey(event, shape)}
            onMouseMove={(event) => track(event, shape.acronym)}
            onFocus={(event) => {
              // Only keyboard focus gets the ring and tooltip; a mouse click also focuses.
              if (!event.currentTarget.matches(":focus-visible")) return;
              setFocused({ acronym: shape.acronym, x: shape.centroid[0], y: shape.centroid[1] });
            }}
            onBlur={() => setFocused(null)}
            className="cursor-pointer fill-[#6b80a3] outline-none transition-[fill] duration-150 hover:fill-[#4a6189] aria-pressed:fill-accent"
          />
        ))}
        {selectedShape && (
          <text
            x={selectedShape.centroid[0]}
            y={selectedShape.centroid[1]}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize="14"
            fontWeight="600"
            fill="#ffffff"
            stroke="var(--accent)"
            strokeWidth="3"
            paintOrder="stroke"
            pointerEvents="none"
            aria-hidden
          >
            {selectedShape.acronym}
          </text>
        )}
        {focusedShape && (
          // Keyboard focus: dashed ring with a white halo, distinct from the selected fill.
          <g pointerEvents="none" aria-hidden data-focus-ring={focusedShape.acronym}>
            <path d={focusedShape.d} fill="none" stroke="#ffffff" strokeWidth={5} strokeLinejoin="round" />
            <path
              d={focusedShape.d}
              fill="none"
              stroke="var(--foreground)"
              strokeWidth={2}
              strokeDasharray="6 3"
              strokeLinejoin="round"
            />
          </g>
        )}
      </svg>
      {tip && tipShape && (
        <div
          role="tooltip"
          className="pointer-events-none absolute z-10 w-max max-w-56 -translate-x-1/2 -translate-y-full rounded-md bg-foreground px-2.5 py-1.5 text-xs text-white shadow-md"
          style={{
            left: `${(tip.x / WIDTH) * 100}%`,
            top: `calc(${(tip.y / HEIGHT) * 100}% - 10px)`,
          }}
        >
          <span className="font-semibold">{tipShape.name}</span>{" "}
          <span className="text-white/70">{tipShape.acronym}</span>
        </div>
      )}
    </div>
  );
}

/** The 27 UFs grouped by region, as compact buttons: a quick alternative to the map. */
function RegionShortcuts({ onSelect }: { onSelect: (acronym: string) => void }) {
  return (
    <div role="group" aria-label="UFs por região" className="mt-4 flex flex-col gap-3">
      {Object.entries(REGION_NAMES).map(([code, name]) => (
        <div key={code} className="flex flex-col gap-1.5">
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">{name}</p>
          <div className="flex flex-wrap gap-1.5">
            {STATES.filter((s) => s.region === code)
              .toSorted((a, b) => a.acronym.localeCompare(b.acronym))
              .map((state) => (
                <button
                  key={state.acronym}
                  type="button"
                  onClick={() => onSelect(state.acronym)}
                  className="min-w-10 rounded-md border border-border bg-background px-2 py-1 text-xs font-medium tabular-nums hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-ring"
                >
                  {state.acronym}
                  {/* The accessible name starts with the visible acronym (WCAG 2.5.3). */}
                  <span className="sr-only"> {state.name}</span>
                </button>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/** Magnifier over a location pin, drawn inline (no icon dependency). */
function ExploreIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="m15.5 15.5 5 5" strokeLinecap="round" />
      <path d="M10.5 13.5s-2.5-2.2-2.5-4a2.5 2.5 0 0 1 5 0c0 1.8-2.5 4-2.5 4Z" fill="currentColor" stroke="none" />
    </svg>
  );
}
