"use client";

import { useId } from "react";

import { Segmented } from "@/components/ui/segmented";
import { PERIOD_PRESETS, type DateRange, type PeriodPreset } from "@/lib/period";

interface Props {
  preset: PeriodPreset;
  range: DateRange;
  minDate: string | null;
  maxDate: string | null;
  onPresetChange: (preset: Exclude<PeriodPreset, "custom">) => void;
  onCustomRange: (range: DateRange) => void;
  invalidRange: boolean;
}

export function PeriodFilter({
  preset,
  range,
  minDate,
  maxDate,
  onPresetChange,
  onCustomRange,
  invalidRange,
}: Props) {
  const startId = useId();
  const endId = useId();
  const errorId = useId();
  const inputClass =
    "rounded-md border border-border bg-card px-2 py-1.5 text-sm text-foreground focus-visible:outline-2 focus-visible:outline-ring aria-invalid:border-red-600";

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="flex flex-col gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Período</span>
        <Segmented
          label="Período predefinido"
          options={PERIOD_PRESETS}
          value={preset === "custom" ? null : preset}
          onChange={onPresetChange}
        />
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label htmlFor={startId} className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
          Data inicial
          <input
            id={startId}
            type="date"
            className={inputClass}
            value={range.start ?? ""}
            min={minDate ?? undefined}
            max={maxDate ?? undefined}
            aria-invalid={invalidRange}
            aria-describedby={invalidRange ? errorId : undefined}
            onChange={(e) => onCustomRange({ start: e.target.value || null, end: range.end })}
          />
        </label>
        <label htmlFor={endId} className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
          Data final
          <input
            id={endId}
            type="date"
            className={inputClass}
            value={range.end ?? ""}
            min={minDate ?? undefined}
            max={maxDate ?? undefined}
            aria-invalid={invalidRange}
            aria-describedby={invalidRange ? errorId : undefined}
            onChange={(e) => onCustomRange({ start: range.start, end: e.target.value || null })}
          />
        </label>
      </div>
      {invalidRange && (
        <p id={errorId} role="alert" className="text-sm text-danger lg:basis-full">
          A data inicial deve ser anterior ou igual à data final.
        </p>
      )}
    </div>
  );
}
