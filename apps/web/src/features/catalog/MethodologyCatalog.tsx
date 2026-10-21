"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorState, InlineError, LoadingState, RefreshingIndicator } from "@/components/ui/states";
import { useIndicators } from "@/hooks/useObservations";

import { IndicatorMetadata } from "./IndicatorMetadata";
import { useScrollToHash } from "./useScrollToHash";

/** Every indicator of the catalog with its metadata, as served by `GET /api/v1/indicators`. */
export function MethodologyCatalog() {
  const state = useIndicators();
  const indicators = state.data;
  useScrollToHash(indicators !== null && indicators.length > 0);

  if (indicators === null) {
    return state.status === "error" ? (
      <ErrorState message={state.error.message} onRetry={state.retry} />
    ) : (
      <LoadingState label="Carregando o catálogo de indicadores…" />
    );
  }
  if (indicators.length === 0) {
    return <EmptyState message="Nenhum indicador cadastrado no catálogo." />;
  }

  return (
    <div className="flex flex-col gap-6">
      {state.status === "error" ? <InlineError message={state.error.message} onRetry={state.retry} /> : null}
      {state.status === "loading" ? <RefreshingIndicator /> : null}
      <nav aria-label="Indicadores do catálogo">
        <ul className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          {indicators.map((indicator) => (
            <li key={indicator.code}>
              <a href={`#${encodeURIComponent(indicator.code)}`} className="underline underline-offset-2">
                {indicator.short_name}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      {indicators.map((indicator) => (
        <Card key={indicator.code} id={indicator.code} aria-labelledby={`${indicator.code}-titulo`} className="scroll-mt-4">
          <CardHeader>
            <h2 id={`${indicator.code}-titulo`} className="text-lg font-semibold">
              {indicator.short_name}
            </h2>
            <p className="text-xs text-muted-foreground">
              Código no Atlas: <code>{indicator.code}</code> · Fonte:{" "}
              <Link href={`/fontes#${encodeURIComponent(indicator.source.acronym)}`} className="underline underline-offset-2">
                {indicator.source.acronym}
              </Link>
            </p>
          </CardHeader>
          <CardContent>
            <IndicatorMetadata indicator={indicator} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
