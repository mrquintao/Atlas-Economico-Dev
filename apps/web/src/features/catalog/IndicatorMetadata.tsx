import { formatDate, formatDateTime } from "@/lib/format";
import type { Indicator, IngestionRun } from "@/types/api";

import { sourceSeriesLabel } from "@/features/dashboard/summary";

const FREQUENCY_LABEL: Record<string, string> = {
  daily: "Diária",
  monthly: "Mensal",
  quarterly: "Trimestral",
  annual: "Anual",
};

export function frequencyLabel(frequency: string): string {
  return FREQUENCY_LABEL[frequency] ?? frequency;
}

/** Shown only when the latest attempt did not succeed: the data above may be outdated. */
export function lastRunLabel(run: IngestionRun, hasSuccessfulCollection: boolean): string {
  const when = `${formatDateTime(run.started_at)} (horário de Brasília)`;
  if (run.status === "running") return `Coleta em andamento desde ${when}.`;
  return hasSuccessfulCollection
    ? `Falhou em ${when}. Os dados exibidos são os da última coleta bem-sucedida.`
    : `Falhou em ${when}. Ainda não há dados coletados deste indicador.`;
}

export function storedRangeLabel(indicator: Indicator): string {
  return indicator.first_stored_date && indicator.last_stored_date
    ? `${formatDate(indicator.first_stored_date)} a ${formatDate(indicator.last_stored_date)}`
    : "Nenhum";
}

/**
 * Catalog metadata of an indicator, exactly as served by the API. Shared by the methodology
 * panel under each chart and by the "Metodologia" page, so no methodological text is
 * duplicated in the frontend.
 */
export function IndicatorMetadata({
  indicator,
  display,
}: {
  indicator: Indicator;
  /** How the chart shows the series (aggregation description from the API), if any. */
  display?: string;
}) {
  return (
    <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
      <dt className="text-muted-foreground">Indicador</dt>
      <dd>{indicator.name}</dd>
      <dt className="text-muted-foreground">Descrição</dt>
      <dd>{indicator.description}</dd>
      <dt className="text-muted-foreground">Unidade</dt>
      <dd>
        {indicator.unit} (variações em {indicator.change_unit})
      </dd>
      <dt className="text-muted-foreground">Frequência original</dt>
      <dd>{frequencyLabel(indicator.frequency)}</dd>
      {display ? (
        <>
          <dt className="text-muted-foreground">Exibição</dt>
          <dd>{display}</dd>
        </>
      ) : null}
      <dt className="text-muted-foreground">Metodologia</dt>
      <dd>{indicator.methodology}</dd>
      {indicator.methodology_version ? (
        <>
          <dt className="text-muted-foreground">Versão da metodologia</dt>
          <dd>{indicator.methodology_version}</dd>
        </>
      ) : null}
      <dt className="text-muted-foreground">Fonte</dt>
      <dd>
        {indicator.source.organization} — {indicator.source.name},{" "}
        {sourceSeriesLabel(indicator)}.{" "}
        <a
          href={indicator.source_url}
          target="_blank"
          rel="noreferrer"
          className="underline underline-offset-2"
        >
          Consultar na fonte oficial
        </a>
      </dd>
      {indicator.first_available_date ? (
        <>
          <dt className="text-muted-foreground">Início da série na fonte</dt>
          <dd>{formatDate(indicator.first_available_date)}</dd>
        </>
      ) : null}
      <dt className="text-muted-foreground">Dados armazenados</dt>
      <dd>{storedRangeLabel(indicator)}</dd>
      <dt className="text-muted-foreground">Última coleta</dt>
      <dd>
        {indicator.last_collected_at
          ? `${formatDateTime(indicator.last_collected_at)} (horário de Brasília)`
          : "Nunca coletado"}
      </dd>
      {indicator.last_run && indicator.last_run.status !== "success" ? (
        <>
          <dt className="text-muted-foreground">Última tentativa</dt>
          <dd>{lastRunLabel(indicator.last_run, indicator.last_collected_at !== null)}</dd>
        </>
      ) : null}
    </dl>
  );
}
