import { formatChange, formatDate, formatMonth, formatRate } from "@/lib/format";
import type { Observation, ObservationsResponse } from "@/types/api";

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
    `Mínima de ${formatRate(stats.min.value, unit)} em ${formatDate(stats.min.date)}; ` +
    `máxima de ${formatRate(stats.max.value, unit)} em ${formatDate(stats.max.date)}.`
  );
}
