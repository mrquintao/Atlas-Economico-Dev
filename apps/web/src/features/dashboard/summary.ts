import { formatChange, formatDate, formatMonth, formatRate } from "@/lib/format";
import type { Indicator, Observation, ObservationsResponse } from "@/types/api";

export interface LatestSummary {
  value: number;
  date: string;
  /** Change versus the value 12 months earlier, when that month exists in the data. */
  change12m: number | null;
  reference12m: string | null;
}

/**
 * Latest value and 12-month change from a monthly (last-value-of-month) series.
 * Returns null when there are no observations.
 */
export function latestFromMonthly(observations: Observation[]): LatestSummary | null {
  const last = observations.at(-1);
  if (!last) return null;
  const [year, month] = last.period_start.split("-");
  const target = `${Number(year) - 1}-${month}-01`;
  const yearAgo = observations.find((o) => o.period_start === target) ?? null;
  return {
    value: last.value,
    date: last.date,
    change12m: yearAgo ? last.value - yearAgo.value : null,
    reference12m: yearAgo ? yearAgo.date : null,
  };
}

/** Plain-language description of the displayed range, used as the chart's accessible label. */
export function describeSeries(response: ObservationsResponse): string {
  const { stats, indicator, unit } = response;
  if (!stats) {
    return `${indicator.short_name}: sem observações no período selecionado.`;
  }
  const fmtDate = response.frequency === "monthly" ? formatMonth : formatDate;
  return (
    `${indicator.short_name} de ${fmtDate(stats.first.date)} a ${fmtDate(stats.last.date)}: ` +
    `passou de ${formatRate(stats.first.value, unit)} para ${formatRate(stats.last.value, unit)} ` +
    `(${formatChange(stats.change, stats.change_unit)}). ` +
    `Mínima de ${formatRate(stats.min.value, unit)} em ${fmtDate(stats.min.date)}; ` +
    `máxima de ${formatRate(stats.max.value, unit)} em ${fmtDate(stats.max.date)}.`
  );
}

type WithFrequency = Pick<Indicator, "frequency">;

/** A reference date in the indicator's own granularity (day for daily, month for monthly). */
export function formatReference(indicator: WithFrequency, date: string): string {
  return indicator.frequency === "daily" ? formatDate(date) : formatMonth(date);
}

/** How the reference date of the latest value is described on its card. */
export function referenceLabel(
  indicator: WithFrequency,
  date: string,
  monthlyPrefix = "Posição de",
): string {
  return indicator.frequency === "daily"
    ? `Vigente em ${formatDate(date)}`
    : `${monthlyPrefix} ${formatMonth(date)}`;
}

/** Name of the official series on the source link, e.g. "SGS 432" or "SIDRA 1737 (v. 2265)". */
export function sourceSeriesLabel(
  indicator: Pick<Indicator, "source" | "source_series_code">,
): string {
  const code = indicator.source_series_code;
  if (indicator.source.acronym === "IBGE") {
    const [table, variable] = code.split("/");
    return variable ? `SIDRA ${table} (v. ${variable})` : `SIDRA ${code}`;
  }
  return `SGS ${code}`;
}
