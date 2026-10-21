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

const CURRENCY_SCALES = [
  { factor: 1e12, suffix: "tri" },
  { factor: 1e9, suffix: "bi" },
  { factor: 1e6, suffix: "mi" },
] as const;

/** Whether a unit is an amount in reais (e.g. "R$ correntes"). */
export function isCurrencyUnit(unit: string): boolean {
  return unit.startsWith("R$");
}

/**
 * An amount in reais, scaled to trillions/billions/millions with the scale written out:
 * 266221395322.55 → "R$ 266,22 bi". With `signed`, positive amounts get "+" (for differences).
 */
export function formatCurrency(value: number, signed = false, decimals = DECIMALS): string {
  const magnitude = Math.abs(value);
  // The scale is chosen after rounding: 999.999.999 is "R$ 1,00 bi", never "R$ 1.000,00 mi".
  const rounded = (factor: number) => Number((magnitude / factor).toFixed(decimals));
  let index = CURRENCY_SCALES.findIndex((s) => magnitude >= s.factor);
  if (index === -1) index = CURRENCY_SCALES.length;
  // Step up while the rounded amount reaches the next scale (1.000 of this one).
  const factorAt = (i: number) => (i < CURRENCY_SCALES.length ? CURRENCY_SCALES[i].factor : 1);
  while (index > 0 && rounded(factorAt(index)) * factorAt(index) >= CURRENCY_SCALES[index - 1].factor) {
    index -= 1;
  }
  const scale = index < CURRENCY_SCALES.length ? CURRENCY_SCALES[index] : undefined;
  const scaled = rounded(factorAt(index));
  const number = formatNumber(scaled, decimals);
  // Same zero rule as formatChange: no sign when the rounded amount is zero.
  const isZero = number === formatNumber(0, decimals);
  const sign = isZero ? "" : value < 0 ? "-" : signed ? "+" : "";
  return `${sign}R$ ${number}${scale ? ` ${scale.suffix}` : ""}`;
}

/** An axis tick: up to two decimals, none when not needed ("0,5", "1", "1,5"). */
export function formatAxisNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(value);
}

/** A level in its unit: amounts in reais are scaled (formatCurrency), rates use formatRate. */
export function formatValue(value: number, unit: string, decimals = DECIMALS): string {
  return isCurrencyUnit(unit) ? formatCurrency(value, false, decimals) : formatRate(value, unit, decimals);
}

/** A difference in its change unit: signed reais for amounts, otherwise formatChange (p.p.). */
export function formatValueChange(value: number, changeUnit: string, decimals = DECIMALS): string {
  return isCurrencyUnit(changeUnit)
    ? formatCurrency(value, true, decimals)
    : formatChange(value, changeUnit, decimals);
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

/** Number of months in each sub-annual period of a frequency. */
const PERIOD_MONTHS = { bimonthly: 2, quarterly: 3, four_monthly: 4 } as const;
const PERIOD_ABBREVIATIONS = { bimonthly: "bim.", quarterly: "trim.", four_monthly: "quadr." } as const;

type PeriodFrequency = "daily" | "monthly" | "bimonthly" | "quarterly" | "four_monthly" | "annual";

/**
 * The reference period of an observation dated on its first day, in the frequency's own
 * granularity: "15/03/2025" (daily), "mar/2025" (monthly), "6º bim./2025" (bimonthly),
 * "3º quadr./2025" (four-monthly), "2025" (annual). With `withMonths`, multi-month periods also
 * name their months: "6º bim./2025 (nov–dez)".
 */
export function formatPeriod(frequency: PeriodFrequency, iso: string, withMonths = false): string {
  if (frequency === "daily") return formatDate(iso);
  if (frequency === "monthly") return formatMonth(iso);
  const { year, month } = parseIsoDate(iso);
  if (frequency === "annual") return String(year);
  const size = PERIOD_MONTHS[frequency];
  const index = Math.floor((month - 1) / size);
  const label = `${index + 1}º ${PERIOD_ABBREVIATIONS[frequency]}/${year}`;
  if (!withMonths) return label;
  const first = MONTHS[index * size];
  const last = MONTHS[index * size + size - 1];
  return `${label} (${first}–${last})`;
}
