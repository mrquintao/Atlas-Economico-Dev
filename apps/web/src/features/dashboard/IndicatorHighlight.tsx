"use client";

import { Card } from "@/components/ui/card";
import { InlineError } from "@/components/ui/states";
import type { ResourceState } from "@/hooks/useObservations";
import type { NationalDashboard } from "@/types/api";

import { IndicatorCard } from "./IndicatorCard";
import type { DashboardIndicator } from "./indicators";
import { latestFromDashboard } from "./summary";

interface Props {
  config: DashboardIndicator;
  /** Shared national dashboard request (one call for every card). */
  dashboard: ResourceState<NationalDashboard> & { retry: () => void };
}

/** Card with the latest official value, independent of the selected period. */
export function IndicatorHighlight({ config, dashboard }: Props) {
  const item = dashboard.data?.indicators.find((i) => i.indicator.code === config.code);

  if (item) {
    return (
      <IndicatorCard
        indicator={item.indicator}
        latest={latestFromDashboard(item)}
        referencePrefix={config.referencePrefix}
      />
    );
  }
  // Same accessible name as the loaded card, so the region is identifiable in every state.
  const headingId = `card-${config.code}`;
  const loading = dashboard.status === "loading";
  return (
    <Card className="p-5" aria-labelledby={headingId} aria-busy={loading}>
      <h3 id={headingId} className="text-sm font-medium text-muted-foreground">
        {config.fallbackName}
      </h3>
      {dashboard.status === "error" ? (
        <div className="mt-2">
          <InlineError message={dashboard.error.message} onRetry={dashboard.retry} />
        </div>
      ) : loading ? (
        <>
          <div className="mt-3 h-8 w-32 animate-pulse rounded bg-muted" aria-hidden />
          <span className="sr-only" role="status">
            Carregando dados oficiais…
          </span>
        </>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">Sem dados disponíveis.</p>
      )}
    </Card>
  );
}
