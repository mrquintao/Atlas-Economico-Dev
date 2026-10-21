import { Card } from "@/components/ui/card";
import { formatPeriod, formatValue, formatValueChange, isCurrencyUnit } from "@/lib/format";
import type { StateDashboardItem } from "@/types/api";

import { sourceSeriesLabel } from "../dashboard/summary";
import { signNote } from "./state-indicators";

/**
 * Latest published value of a state indicator, with its reference period, accumulation window
 * and the difference to the same period one year earlier (never a neighbouring period).
 */
export function StateIndicatorCard({ item }: { item: StateDashboardItem }) {
  const { indicator, latest, change_12m: change } = item;
  const headingId = `card-${indicator.code}`;
  return (
    <Card className="flex flex-col p-5" aria-labelledby={headingId}>
      <h3 id={headingId} className="text-sm font-medium text-muted-foreground">
        {indicator.short_name}
      </h3>
      {latest ? (
        <>
          <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight">
            {formatValue(latest.value, indicator.unit)}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Referência:{" "}
            <time dateTime={latest.period_start}>
              {formatPeriod(indicator.frequency, latest.period_start, true)}
            </time>
            {isCurrencyUnit(indicator.unit) ? ` · ${indicator.unit}` : null}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{item.accumulation_window}</p>
          {signNote(indicator.code) && (
            <p className="mt-1 text-xs text-muted-foreground">{signNote(indicator.code)}</p>
          )}
          {change ? (
            <div className="mt-3 text-sm">
              <p>
                <span className="font-medium tabular-nums">
                  {formatValueChange(change.value, change.change_unit)}
                </span>{" "}
                <span className="text-muted-foreground">
                  em relação ao{" "}
                  {formatPeriod(indicator.frequency, change.reference_date)} (
                  {formatValue(change.reference_value, indicator.unit)})
                </span>
              </p>
              {item.change_note && (
                <p className="mt-1 text-xs text-muted-foreground">{item.change_note}</p>
              )}
            </div>
          ) : (
            <p className="mt-3 text-xs text-muted-foreground">
              Não há valor armazenado para o mesmo período do ano anterior; por isso, não há
              comparação.
            </p>
          )}
        </>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">Sem dados disponíveis.</p>
      )}
      <p className="mt-auto pt-4 text-xs text-muted-foreground">
        Fonte:{" "}
        <a
          href={indicator.source_url}
          target="_blank"
          rel="noreferrer"
          className="underline underline-offset-2 hover:text-foreground"
        >
          {indicator.source.organization} — {sourceSeriesLabel(indicator)}
        </a>
      </p>
    </Card>
  );
}
