/** Reusable pt-BR formatting. All user-visible numbers and dates go through here. */

const DECIMALS = 2;

function numberFormatter(decimals: number, signed = false): Intl.NumberFormat {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
    signDisplay: signed ? "exceptZero" : "auto",
  });
}

export function formatNumber(value: number, decimals = DECIMALS): string {
  return numberFormatter(decimals).format(value);
}

/** A rate level, e.g. 13.75 + "% a.a." → "13,75% a.a." */
export function formatRate(value: number, unit: string, decimals = DECIMALS): string {
  const number = formatNumber(value, decimals);
  if (unit.startsWith("%")) {
    return `${number}${unit}`;
  }
  return `${number} ${unit}`;
}

/**
 * An absolute difference between two observations, in the indicator's change unit.
 * For rates this is percentage points: 10% → 12% is "+2,00 p.p.", never "+2%".
 */
export function formatChange(value: number, changeUnit: string, decimals = DECIMALS): string {
  // Avoid "-0,00" for tiny floating point residues.
  const rounded = Math.abs(value) < 0.5 * 10 ** -decimals ? 0 : value;
  return `${numberFormatter(decimals, true).format(rounded)} ${changeUnit}`;
}

/** Parses an ISO date (YYYY-MM-DD) as a calendar date, without timezone shifts. */
export function parseIsoDate(iso: string): { year: number; month: number; day: number } {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!match) {
    throw new Error(`Data ISO inválida: ${iso}`);
  }
  return { year: Number(match[1]), month: Number(match[2]), day: Number(match[3]) };
}

export function formatDate(iso: string): string {
  const { year, month, day } = parseIsoDate(iso);
  return `${String(day).padStart(2, "0")}/${String(month).padStart(2, "0")}/${year}`;
}

const MONTHS = [
  "jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez",
] as const;

export function formatMonth(iso: string): string {
  const { year, month } = parseIsoDate(iso);
  return `${MONTHS[month - 1]}/${year}`;
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(iso));
}
