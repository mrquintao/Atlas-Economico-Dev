"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorState, InlineError, LoadingState, RefreshingIndicator } from "@/components/ui/states";
import { useIndicators, useSources } from "@/hooks/useObservations";
import type { Indicator, Source } from "@/types/api";

import { sourceSeriesLabel } from "@/features/dashboard/summary";

import { useScrollToHash } from "./useScrollToHash";

function SourceIndicators({ indicators }: { indicators: Indicator[] }) {
  if (indicators.length === 0) {
    return <dd>Nenhum indicador do catálogo usa esta fonte.</dd>;
  }
  return (
    <dd>
      <ul className="flex flex-col gap-1">
        {indicators.map((indicator) => (
          <li key={indicator.code}>
            <Link
              href={`/metodologia#${encodeURIComponent(indicator.code)}`}
              className="underline underline-offset-2"
            >
              {indicator.short_name}
            </Link>{" "}
            — {sourceSeriesLabel(indicator)} (
            <a
              href={indicator.source_url}
              target="_blank"
              rel="noreferrer"
              className="underline underline-offset-2"
            >
              série oficial
            </a>
            )
          </li>
        ))}
      </ul>
    </dd>
  );
}

function SourceCard({ source, indicators }: { source: Source; indicators: Indicator[] | null }) {
  const titleId = `${source.acronym}-titulo`;
  return (
    <Card id={source.acronym} aria-labelledby={titleId} className="scroll-mt-4">
      <CardHeader>
        <h2 id={titleId} className="text-lg font-semibold">
          {source.organization} ({source.acronym})
        </h2>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
          <dt className="text-muted-foreground">Sistema</dt>
          <dd>{source.name}</dd>
          <dt className="text-muted-foreground">Endereço consultado pelo Atlas</dt>
          <dd>
            <code className="break-all">{source.base_url}</code>
          </dd>
          <dt className="text-muted-foreground">Documentação</dt>
          <dd>
            {source.documentation_url ? (
              <a
                href={source.documentation_url}
                target="_blank"
                rel="noreferrer"
                className="break-all underline underline-offset-2"
              >
                {source.documentation_url}
              </a>
            ) : (
              "Não informada"
            )}
          </dd>
          {indicators ? (
            <>
              <dt className="text-muted-foreground">Indicadores</dt>
              <SourceIndicators indicators={indicators} />
            </>
          ) : null}
        </dl>
      </CardContent>
    </Card>
  );
}

/**
 * Official sources (`GET /api/v1/sources`) and the catalog indicators each one feeds
 * (`GET /api/v1/indicators`). The sources render even if the indicator list fails.
 */
export function SourcesCatalog() {
  const sourcesState = useSources();
  const indicatorsState = useIndicators();
  const sources = sourcesState.data;
  const indicators = indicatorsState.data;
  // Wait for the indicator lists too: they grow the cards above the target.
  useScrollToHash(
    sources !== null && sources.length > 0 && indicatorsState.status !== "loading",
  );

  if (sources === null) {
    return sourcesState.status === "error" ? (
      <ErrorState message={sourcesState.error.message} onRetry={sourcesState.retry} />
    ) : (
      <LoadingState label="Carregando as fontes oficiais…" />
    );
  }
  if (sources.length === 0) {
    return <EmptyState message="Nenhuma fonte cadastrada no catálogo." />;
  }

  return (
    <div className="flex flex-col gap-6">
      {sourcesState.status === "error" ? (
        <InlineError message={sourcesState.error.message} onRetry={sourcesState.retry} />
      ) : null}
      {indicatorsState.status === "error" ? (
        <InlineError
          message={`Não foi possível carregar os indicadores de cada fonte. ${indicatorsState.error.message}`}
          onRetry={indicatorsState.retry}
        />
      ) : null}
      {sourcesState.status === "loading" || indicatorsState.status === "loading" ? (
        <RefreshingIndicator label={indicators === null ? "Carregando indicadores…" : "Atualizando…"} />
      ) : null}
      {sources.map((source) => (
        <SourceCard
          key={source.acronym}
          source={source}
          indicators={
            indicators === null ? null : indicators.filter((i) => i.source.acronym === source.acronym)
          }
        />
      ))}
    </div>
  );
}
