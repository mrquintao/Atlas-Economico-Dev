import { formatDate, formatMonth, formatPeriod, formatValue, formatValueChange } from "@/lib/format";
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
  const { stats, indicator, unit, observations } = response;
  const fmtDate = (date: string) => formatPeriod(response.frequency, date);
  if (!stats) {
    const first = observations[0];
    const last = observations.at(-1);
    if (!first || !last) {
      return `${indicator.short_name}: sem observações no período selecionado.`;
    }
    // No change, minimum or maximum (e.g. year-to-date flows, whose periods are not comparable).
    return (
      `${indicator.short_name} de ${fmtDate(first.date)} a ${fmtDate(last.date)}: ` +
      `${observations.length} ${observations.length === 1 ? "valor publicado" : "valores publicados"}; ` +
      `o último é ${formatValue(last.value, unit)}.`
    );
  }
  return (
    `${indicator.short_name} de ${fmtDate(stats.first.date)} a ${fmtDate(stats.last.date)}: ` +
    `passou de ${formatValue(stats.first.value, unit)} para ${formatValue(stats.last.value, unit)} ` +
    `(${formatValueChange(stats.change, stats.change_unit)}). ` +
    `Mínima de ${formatValue(stats.min.value, unit)} em ${fmtDate(stats.min.date)}; ` +
    `máxima de ${formatValue(stats.max.value, unit)} em ${fmtDate(stats.max.date)}.`
  );
}

type WithFrequency = Pick<Indicator, "frequency">;

/** A reference date in the indicator's own granularity (day, month, bimester…). */
export function formatReference(indicator: WithFrequency, date: string): string {
  return formatPeriod(indicator.frequency, date);
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
