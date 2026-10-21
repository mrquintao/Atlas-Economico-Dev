import { formatChange, formatDate, formatMonth, formatRate } from "@/lib/format";
import type { Indicator, NationalDashboardItem, ObservationsResponse } from "@/types/api";

export interface LatestSummary {
  value: number;
  date: string;
  /** Change versus the value 12 months earlier, when that month exists in the data. */
  change12m: number | null;
  reference12m: string | null;
}

/**
 * Card summary from the national dashboard endpoint, which computes the latest value and the
 * 12-month change on the server. Returns null when the indicator has no stored data.
 */
export function latestFromDashboard(item: NationalDashboardItem): LatestSummary | null {
  if (!item.latest) return null;
  return {
    value: item.latest.value,
    date: item.latest.date,
    change12m: item.change_12m?.value ?? null,
    reference12m: item.change_12m?.reference_date ?? null,
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
  if (indicator.source.acronym === "SICONFI") return `SICONFI, ${code}`;
  return `SGS ${code}`;
}
