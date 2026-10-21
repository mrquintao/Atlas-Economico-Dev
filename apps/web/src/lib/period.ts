/** Period presets and date-range arithmetic shared by all charts (they use the same range). */

export type PeriodPreset = "5y" | "10y" | "since2008" | "all" | "custom";

export interface DateRange {
  /** ISO date (YYYY-MM-DD) or null for "from the first available observation". */
  start: string | null;
  /** ISO date or null for "until the latest available observation". */
  end: string | null;
}

export const PERIOD_PRESETS: { value: Exclude<PeriodPreset, "custom">; label: string }[] = [
  { value: "5y", label: "5 anos" },
  { value: "10y", label: "10 anos" },
  { value: "since2008", label: "Desde 2008" },
  { value: "all", label: "Todo o histórico" },
];

/** Default initial period of the national dashboard (PROJECT_SPEC §5). */
export const DEFAULT_PRESET: PeriodPreset = "since2008";
export const SINCE_2008_START = "2008-01-01";

function toIso(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Subtracts whole years from an ISO date (29/02 falls back to 28/02). */
export function subtractYears(iso: string, years: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const target = new Date(Date.UTC(y - years, m - 1, d));
  if (target.getUTCMonth() !== m - 1) {
    target.setUTCDate(0);
  }
  return toIso(target);
}

/** First day of the month of an ISO date. */
export function startOfMonth(iso: string): string {
  return `${iso.slice(0, 7)}-01`;
}

/**
 * Range for a preset. `anchor` is the reference end date (normally the latest available
 * observation), so "5 anos" means the five years up to the most recent official value. Relative
 * presets start on the 1st of the month, so monthly series show their first month in full.
 */
export function rangeForPreset(preset: Exclude<PeriodPreset, "custom">, anchor: string): DateRange {
  switch (preset) {
    case "5y":
      return { start: startOfMonth(subtractYears(anchor, 5)), end: null };
    case "10y":
      return { start: startOfMonth(subtractYears(anchor, 10)), end: null };
    case "since2008":
      return { start: SINCE_2008_START, end: null };
    case "all":
      return { start: null, end: null };
  }
}

export function isValidRange(range: DateRange): boolean {
  return range.start === null || range.end === null || range.start <= range.end;
}

/** Today's date in the viewer's local calendar (not UTC), as an ISO date. */
export function todayLocalIso(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}
