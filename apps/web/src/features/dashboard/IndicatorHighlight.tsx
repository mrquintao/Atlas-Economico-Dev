"use client";

import { useMemo } from "react";

import { Card } from "@/components/ui/card";
import { InlineError } from "@/components/ui/states";
import { useObservations } from "@/hooks/useObservations";
import type { DateRange } from "@/lib/period";

import { IndicatorCard } from "./IndicatorCard";
import type { DashboardIndicator } from "./indicators";
import { latestFromMonthly } from "./summary";

const FULL_HISTORY: DateRange = { start: null, end: null };

/** Card with the latest official value, independent of the selected period. */
export function IndicatorHighlight({ config }: { config: DashboardIndicator }) {
  // Monthly view: one point per month is enough for "latest" and "12-month change".
  const latest = useObservations(config.code, FULL_HISTORY, "monthly");
  const summary = useMemo(
    () => (latest.data ? latestFromMonthly(latest.data.observations) : null),
    [latest.data],
  );

  if (latest.data) {
    return <IndicatorCard
        indicator={latest.data.indicator}
        latest={summary}
        referencePrefix={config.referencePrefix}
      />;
  }
  // Same accessible name as the loaded card, so the region is identifiable in every state.
  const headingId = `card-${config.code}`;
  return (
    <Card className="p-5" aria-labelledby={headingId} aria-busy={latest.status === "loading"}>
      <h3 id={headingId} className="text-sm font-medium text-muted-foreground">
        {config.fallbackName}
      </h3>
      {latest.status === "error" ? (
        <div className="mt-2">
          <InlineError message={latest.error.message} onRetry={latest.retry} />
        </div>
      ) : (
        <>
          <div className="mt-3 h-8 w-32 animate-pulse rounded bg-muted" aria-hidden />
          <span className="sr-only" role="status">
            Carregando dados oficiais…
          </span>
        </>
      )}
    </Card>
  );
}
