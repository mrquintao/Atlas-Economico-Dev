import { Card } from "@/components/ui/card";
import { formatChange, formatRate } from "@/lib/format";
import type { Indicator } from "@/types/api";

import {
  formatReference,
  referenceLabel,
  sourceSeriesLabel,
  type LatestSummary,
} from "./summary";

interface Props {
  indicator: Indicator;
  latest: LatestSummary | null;
  referencePrefix?: string;
}

export function IndicatorCard({ indicator, latest, referencePrefix }: Props) {
  return (
    <Card className="p-5" aria-labelledby={`card-${indicator.code}`}>
      <h3 id={`card-${indicator.code}`} className="text-sm font-medium text-muted-foreground">
        {indicator.short_name}
      </h3>
      {latest ? (
        <>
          <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight">
            {formatRate(latest.value, indicator.unit)}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            <time dateTime={latest.date}>{referenceLabel(indicator, latest.date, referencePrefix)}</time>
          </p>
          {latest.change12m !== null && latest.reference12m && (
            <p className="mt-3 text-sm">
              <span className="font-medium tabular-nums">
                {formatChange(latest.change12m, indicator.change_unit)}
              </span>{" "}
              <span className="text-muted-foreground">
                em 12 meses (vs. {formatReference(indicator, latest.reference12m)})
              </span>
            </p>
          )}
        </>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">Sem dados disponíveis.</p>
      )}
      <p className="mt-4 text-xs text-muted-foreground">
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
