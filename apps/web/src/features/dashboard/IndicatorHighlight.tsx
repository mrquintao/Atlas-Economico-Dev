"use client";

import { useMemo } from "react";

import { Card } from "@/components/ui/card";
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
    return <IndicatorCard indicator={latest.data.indicator} latest={summary} />;
  }
  return (
    <Card className="p-5" role={latest.status === "error" ? "alert" : undefined} aria-busy={latest.status === "loading"}>
      <h3 className="text-sm font-medium text-muted-foreground">{config.fallbackName}</h3>
      {latest.status === "error" ? (
        <p className="mt-2 text-sm">{latest.error.message}</p>
      ) : (
        <div className="mt-3 h-8 w-32 animate-pulse rounded bg-muted" />
      )}
    </Card>
  );
}
