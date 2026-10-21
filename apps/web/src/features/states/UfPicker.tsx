"use client";

import { REGION_NAMES, STATES } from "@/lib/states";

interface Props {
  legend: string;
  /** Selected acronyms, in selection order. */
  selected: readonly string[];
  onChange: (next: string[]) => void;
  /** Maximum number of UFs: further boxes are disabled once it is reached. */
  max?: number;
  /** Shows "Todas" and "Nenhuma" shortcuts. */
  bulk?: boolean;
}

const REGIONS = Object.entries(REGION_NAMES).map(([code, name]) => ({
  code,
  name,
  states: STATES.filter((s) => s.region === code).toSorted((a, b) => a.acronym.localeCompare(b.acronym)),
}));

/** Checkboxes of the 27 UFs grouped by region; the order of selection is kept. */
export function UfPicker({ legend, selected, onChange, max, bulk = false }: Props) {
  const chosen = new Set(selected);
  const full = max !== undefined && selected.length >= max;

  function toggle(acronym: string, checked: boolean) {
    onChange(checked ? [...selected, acronym] : selected.filter((uf) => uf !== acronym));
  }

  return (
    <fieldset className="flex flex-col gap-2 text-sm">
      <legend className="mb-1 text-xs font-medium text-muted-foreground">{legend}</legend>
      {bulk && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onChange(STATES.map((s) => s.acronym).toSorted())}
            className="rounded-md border border-border px-2.5 py-1 text-xs font-medium hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
          >
            Todas
          </button>
          <button
            type="button"
            onClick={() => onChange([])}
            className="rounded-md border border-border px-2.5 py-1 text-xs font-medium hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
          >
            Nenhuma
          </button>
        </div>
      )}
      <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-5">
        {REGIONS.map((region) => (
          <div key={region.code} role="group" aria-label={region.name} className="flex flex-col gap-1">
            <span aria-hidden className="text-xs text-muted-foreground">
              {region.name}
            </span>
            <div className="flex flex-wrap gap-x-3 gap-y-1">
              {region.states.map((state) => {
                const checked = chosen.has(state.acronym);
                return (
                  <label key={state.acronym} title={state.name} className="inline-flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={!checked && full}
                      onChange={(event) => toggle(state.acronym, event.target.checked)}
                      aria-label={state.name}
                    />
                    {state.acronym}
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </fieldset>
  );
}
