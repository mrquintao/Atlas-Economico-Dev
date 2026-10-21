import { formatDate, formatDateTime } from "@/lib/format";
import type { IngestionRun, ObservationsResponse } from "@/types/api";

import { sourceSeriesLabel } from "./summary";

const FREQUENCY_LABEL: Record<string, string> = {
  daily: "Diária",
  monthly: "Mensal",
  quarterly: "Trimestral",
  annual: "Anual",
};

/** Shown only when the latest attempt did not succeed: the data above may be outdated. */
export function lastRunLabel(run: IngestionRun): string {
  const when = `${formatDateTime(run.started_at)} (horário de Brasília)`;
  if (run.status === "running") return `Coleta em andamento desde ${when}.`;
  return (
    `Falhou em ${when}. Os dados exibidos são os da última coleta bem-sucedida; ` +
    "uma nova tentativa ocorre na próxima atualização programada."
  );
}

export function MethodologyPanel({ response }: { response: ObservationsResponse }) {
  const { indicator, aggregation } = response;
  return (
    <details className="group rounded-lg border border-border bg-muted/40 p-4 text-sm">
      <summary className="cursor-pointer font-medium focus-visible:outline-2 focus-visible:outline-ring">
        Sobre o indicador e a metodologia
      </summary>
      <dl className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-[max-content_1fr]">
        <dt className="text-muted-foreground">Indicador</dt>
        <dd>{indicator.name}</dd>
        <dt className="text-muted-foreground">Descrição</dt>
        <dd>{indicator.description}</dd>
        <dt className="text-muted-foreground">Unidade</dt>
        <dd>
          {indicator.unit} (variações em {indicator.change_unit})
        </dd>
        <dt className="text-muted-foreground">Frequência original</dt>
        <dd>{FREQUENCY_LABEL[indicator.frequency] ?? indicator.frequency}</dd>
        <dt className="text-muted-foreground">Exibição</dt>
        <dd>{aggregation.description}</dd>
        <dt className="text-muted-foreground">Metodologia</dt>
        <dd>{indicator.methodology}</dd>
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
        <dt className="text-muted-foreground">Dados armazenados</dt>
        <dd>
          {indicator.first_stored_date && indicator.last_stored_date
            ? `${formatDate(indicator.first_stored_date)} a ${formatDate(indicator.last_stored_date)}`
            : "Nenhum"}
        </dd>
        <dt className="text-muted-foreground">Última coleta</dt>
        <dd>
          {indicator.last_collected_at
            ? `${formatDateTime(indicator.last_collected_at)} (horário de Brasília)`
            : "Nunca coletado"}
        </dd>
        {indicator.last_run && indicator.last_run.status !== "success" ? (
          <>
            <dt className="text-muted-foreground">Última tentativa</dt>
            <dd>{lastRunLabel(indicator.last_run)}</dd>
          </>
        ) : null}
      </dl>
    </details>
  );
}
