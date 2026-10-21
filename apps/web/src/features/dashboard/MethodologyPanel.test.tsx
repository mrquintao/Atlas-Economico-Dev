import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { IngestionRun, ObservationsResponse } from "@/types/api";

import { lastRunLabel } from "@/features/catalog/IndicatorMetadata";

import { MethodologyPanel } from "./MethodologyPanel";

// ---- Synthetic API response (test-only data) ----

function response(lastRun: IngestionRun | null): ObservationsResponse {
  return {
    indicator: {
      code: "SELIC_TARGET",
      name: "Meta Selic",
      short_name: "Meta Selic",
      description: "Meta para a taxa Selic.",
      unit: "% a.a.",
      change_unit: "p.p.",
      frequency: "daily",
      geographic_level: "country",
      methodology: "Série SGS 432.",
      methodology_version: null,
      first_available_date: "1999-03-05",
      source: {
        acronym: "BCB",
        name: "SGS",
        organization: "Banco Central do Brasil",
        base_url: "https://api.bcb.gov.br/dados/serie",
        documentation_url: null,
      },
      source_series_code: "432",
      source_url: "https://dadosabertos.bcb.gov.br/dataset/432",
      first_stored_date: "1999-03-05",
      last_stored_date: "2026-10-20",
      last_collected_at: "2026-10-20T09:00:10Z",
      last_run: lastRun,
    },
    geography: { ibge_code: "1", acronym: "BR", name: "Brasil", geographic_level: "country" },
    unit: "% a.a.",
    original_frequency: "daily",
    frequency: "daily",
    aggregation: { method: "none", description: "Valores originais." },
    start_date: null,
    end_date: null,
    count: 0,
    stats: null,
    observations: [],
  };
}

const failed: IngestionRun = {
  status: "failed",
  started_at: "2026-10-21T09:00:00Z",
  finished_at: "2026-10-21T09:00:31Z",
  error_type: "SGSUnavailableError",
};

describe("MethodologyPanel", () => {
  it("shows only the last successful collection when the latest run succeeded", () => {
    render(
      <MethodologyPanel
        response={response({ ...failed, status: "success", error_type: null })}
      />,
    );
    expect(screen.getByText("20/10/2026, 06:00 (horário de Brasília)")).toBeInTheDocument();
    expect(screen.queryByText("Última tentativa")).not.toBeInTheDocument();
  });

  it("warns that the data may be outdated when the latest run failed", () => {
    render(<MethodologyPanel response={response(failed)} />);
    expect(screen.getByText("Última tentativa")).toBeInTheDocument();
    expect(screen.getByText(/^Falhou em 21\/10\/2026, 06:00 \(horário de Brasília\)/)).toBeInTheDocument();
    // The last successful collection is still shown.
    expect(screen.getByText("20/10/2026, 06:00 (horário de Brasília)")).toBeInTheDocument();
  });

  it("does not claim stored data when the first collection failed", () => {
    const body = response(failed);
    body.indicator.last_collected_at = null;
    render(<MethodologyPanel response={body} />);
    expect(screen.getByText("Nunca coletado")).toBeInTheDocument();
    expect(screen.getByText(/Ainda não há dados coletados deste indicador\.$/)).toBeInTheDocument();
    expect(screen.queryByText(/última coleta bem-sucedida/)).not.toBeInTheDocument();
  });

  it("links to the indicator on the methodology page", () => {
    render(<MethodologyPanel response={response(null)} />);
    expect(
      screen.getByRole("link", { name: "Ver todos os indicadores na página de metodologia" }),
    ).toHaveAttribute("href", "/metodologia#SELIC_TARGET");
  });

  it("does not show a run status for an indicator never collected", () => {
    render(<MethodologyPanel response={response(null)} />);
    expect(screen.queryByText("Última tentativa")).not.toBeInTheDocument();
  });
});

describe("lastRunLabel", () => {
  it("describes a collection in progress", () => {
    expect(lastRunLabel({ ...failed, status: "running", finished_at: null }, true)).toBe(
      "Coleta em andamento desde 21/10/2026, 06:00 (horário de Brasília).",
    );
  });

  it("says the displayed data come from the last successful collection", () => {
    expect(lastRunLabel(failed, true)).toBe(
      "Falhou em 21/10/2026, 06:00 (horário de Brasília). Os dados exibidos são os da última coleta bem-sucedida.",
    );
  });
});
