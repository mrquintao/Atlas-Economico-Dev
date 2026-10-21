import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Indicator, Source } from "@/types/api";

import { MethodologyCatalog } from "./MethodologyCatalog";
import { SourcesCatalog } from "./SourcesCatalog";

// ---- Synthetic API responses (test-only data) ----

const bcb: Source = {
  acronym: "BCB",
  name: "Sistema Gerenciador de Séries Temporais (SGS)",
  organization: "Banco Central do Brasil",
  base_url: "https://api.bcb.gov.br/dados/serie",
  documentation_url: "https://dadosabertos.bcb.gov.br/",
};

const ibge: Source = {
  acronym: "IBGE",
  name: "Sistema IBGE de Recuperação Automática (SIDRA)",
  organization: "Instituto Brasileiro de Geografia e Estatística",
  base_url: "https://apisidra.ibge.gov.br",
  documentation_url: null,
};

const selic: Indicator = {
  code: "SELIC_TARGET",
  name: "Taxa de juros - Meta Selic definida pelo Copom",
  short_name: "Meta Selic",
  description: "Descrição sintética da Meta Selic.",
  unit: "% a.a.",
  change_unit: "p.p.",
  frequency: "daily",
  geographic_level: "country",
  methodology: "Metodologia sintética servida pela API.",
  methodology_version: "SGS 432",
  first_available_date: "1999-03-05",
  source: bcb,
  source_series_code: "432",
  source_url: "https://dadosabertos.bcb.gov.br/dataset/432",
  first_stored_date: "1999-03-05",
  last_stored_date: "2026-10-20",
  last_collected_at: "2026-10-20T09:00:10Z",
  last_run: {
    status: "success",
    started_at: "2026-10-20T09:00:00Z",
    finished_at: "2026-10-20T09:00:10Z",
    error_type: null,
  },
};

const ipca: Indicator = {
  ...selic,
  code: "IPCA_12M",
  name: "IPCA - Variação acumulada em 12 meses",
  short_name: "IPCA 12 meses",
  description: "Descrição sintética do IPCA.",
  unit: "%",
  frequency: "monthly",
  methodology: "Outra metodologia sintética.",
  methodology_version: null,
  first_available_date: null,
  source: ibge,
  source_series_code: "1737/2265",
  source_url: "https://sidra.ibge.gov.br/tabela/1737",
  first_stored_date: null,
  last_stored_date: null,
  last_collected_at: null,
  last_run: {
    status: "failed",
    started_at: "2026-10-21T09:00:00Z",
    finished_at: "2026-10-21T09:00:31Z",
    error_type: "SidraUnavailableError",
  },
};

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const unavailable = { error: { code: "database_unavailable", message: "Banco de dados indisponível." } };

let routes: Record<string, () => Response>;
let fetchMock: ReturnType<typeof vi.fn>;

function calls(path: string): number {
  return fetchMock.mock.calls.filter(([url]) => new URL(String(url)).pathname === path).length;
}

beforeEach(() => {
  routes = {
    "/api/v1/sources": () => json([bcb, ibge]),
    "/api/v1/indicators": () => json([ipca, selic]),
  };
  fetchMock = vi.fn(async (url: string) => {
    const route = routes[new URL(url).pathname];
    return route ? route() : json({ error: { code: "not_found", message: "?" } }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.location.hash = "";
});

describe("MethodologyCatalog", () => {
  it("lists every indicator with the metadata served by the API", async () => {
    render(<MethodologyCatalog />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando o catálogo de indicadores…");

    const selicCard = await screen.findByRole("region", { name: "Meta Selic" });
    expect(selicCard).toHaveAttribute("id", "SELIC_TARGET");
    const card = within(selicCard);
    expect(card.getByText("Descrição sintética da Meta Selic.")).toBeInTheDocument();
    expect(card.getByText("Metodologia sintética servida pela API.")).toBeInTheDocument();
    expect(card.getByText("SGS 432")).toBeInTheDocument();
    expect(card.getByText("% a.a. (variações em p.p.)")).toBeInTheDocument();
    expect(card.getByText("Diária")).toBeInTheDocument();
    expect(card.getByText("Nacional (Brasil)")).toBeInTheDocument();
    expect(card.getByText("05/03/1999 a 20/10/2026")).toBeInTheDocument();
    expect(card.getByText("20/10/2026, 06:00 (horário de Brasília)")).toBeInTheDocument();
    expect(card.getByRole("link", { name: "Consultar na fonte oficial" })).toHaveAttribute(
      "href",
      "https://dadosabertos.bcb.gov.br/dataset/432",
    );
    expect(card.getByRole("link", { name: "BCB" })).toHaveAttribute("href", "/fontes#BCB");
    // Exibição belongs to a chart, not to the catalog.
    expect(card.queryByText("Exibição")).not.toBeInTheDocument();

    const ipcaCard = within(screen.getByRole("region", { name: "IPCA 12 meses" }));
    expect(ipcaCard.getByText(/SIDRA 1737 \(v\. 2265\)/)).toBeInTheDocument();
    expect(ipcaCard.getByText("Nenhum")).toBeInTheDocument();
    expect(ipcaCard.getByText("Nunca coletado")).toBeInTheDocument();
    expect(ipcaCard.getByText(/Ainda não há dados coletados deste indicador\.$/)).toBeInTheDocument();
    expect(ipcaCard.queryByText("Início da série na fonte")).not.toBeInTheDocument();
    expect(ipcaCard.queryByText("Versão da metodologia")).not.toBeInTheDocument();

    const toc = within(screen.getByRole("navigation", { name: "Indicadores do catálogo" }));
    expect(toc.getByRole("link", { name: "Meta Selic" })).toHaveAttribute("href", "#SELIC_TARGET");
  });

  it("labels state indicators by coverage and four-month frequency", async () => {
    const siconfi: Source = { ...bcb, acronym: "SICONFI", organization: "Secretaria do Tesouro Nacional" };
    const dcl: Indicator = {
      ...selic,
      code: "STATE_DCL",
      short_name: "DCL",
      frequency: "four_monthly",
      geographic_level: "state",
      source: siconfi,
      source_series_code: "RGF-Anexo 02",
      first_stored_date: "2018-01-01",
      last_stored_date: "2026-05-01",
    };
    routes["/api/v1/indicators"] = () => json([dcl]);
    render(<MethodologyCatalog />);
    const card = within(await screen.findByRole("region", { name: "DCL" }));
    expect(card.getByText("Quadrimestral")).toBeInTheDocument();
    expect(card.getByText("Estadual (cada UF separadamente)")).toBeInTheDocument();
    expect(card.getByText(/SICONFI, RGF-Anexo 02/)).toBeInTheDocument();
    expect(
      card.getByText("01/01/2018 a 01/05/2026 (considerando todas as UFs; a cobertura varia por UF)"),
    ).toBeInTheDocument();
  });

  it("shows an error with retry and recovers", async () => {
    routes["/api/v1/indicators"] = () => json(unavailable, 503);
    render(<MethodologyCatalog />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Banco de dados indisponível.");

    routes["/api/v1/indicators"] = () => json([selic]);
    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("region", { name: "Meta Selic" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(calls("/api/v1/indicators")).toBe(2);
  });

  it("shows an empty state when the catalog has no indicators", async () => {
    routes["/api/v1/indicators"] = () => json([]);
    render(<MethodologyCatalog />);
    expect(await screen.findByText("Nenhum indicador cadastrado no catálogo.")).toBeInTheDocument();
  });

  it("scrolls to the indicator named in the URL hash once loaded", async () => {
    const scroll = vi.fn();
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scroll;
    window.location.hash = "#IPCA_12M";
    try {
      render(<MethodologyCatalog />);
      await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));
      expect(scroll.mock.contexts[0]).toHaveAttribute("id", "IPCA_12M");
    } finally {
      Element.prototype.scrollIntoView = original;
    }
  });

  it("does not crash on a malformed URL hash", async () => {
    window.location.hash = "#%E0";
    render(<MethodologyCatalog />);
    expect(await screen.findByRole("region", { name: "Meta Selic" })).toBeInTheDocument();
  });
});

describe("SourcesCatalog", () => {
  it("scrolls to the source in the URL hash only after the indicator lists load", async () => {
    const scroll = vi.fn();
    const original = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scroll;
    window.location.hash = "#IBGE";
    let releaseIndicators: () => void = () => {};
    const indicatorsReady = new Promise<void>((resolve) => {
      releaseIndicators = resolve;
    });
    fetchMock.mockImplementation(async (url: string) => {
      const path = new URL(url).pathname;
      if (path === "/api/v1/indicators") await indicatorsReady;
      return routes[path]();
    });
    try {
      render(<SourcesCatalog />);
      await screen.findByRole("region", { name: "Banco Central do Brasil (BCB)" });
      expect(scroll).not.toHaveBeenCalled();
      releaseIndicators();
      await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));
      expect(scroll.mock.contexts[0]).toHaveAttribute("id", "IBGE");
      expect(screen.getByRole("link", { name: "IPCA 12 meses" })).toBeInTheDocument();
    } finally {
      Element.prototype.scrollIntoView = original;
    }
  });

  it("lists every source with the indicators it feeds", async () => {
    render(<SourcesCatalog />);
    expect(screen.getByRole("status")).toHaveTextContent("Carregando as fontes oficiais…");

    const bcbCard = await screen.findByRole("region", { name: "Banco Central do Brasil (BCB)" });
    expect(bcbCard).toHaveAttribute("id", "BCB");
    const card = within(bcbCard);
    expect(card.getByText("Sistema Gerenciador de Séries Temporais (SGS)")).toBeInTheDocument();
    expect(card.getByText("https://api.bcb.gov.br/dados/serie")).toBeInTheDocument();
    expect(card.getByRole("link", { name: "https://dadosabertos.bcb.gov.br/" })).toBeInTheDocument();
    expect(await card.findByRole("link", { name: "Meta Selic" })).toHaveAttribute(
      "href",
      "/metodologia#SELIC_TARGET",
    );
    expect(card.getByText(/SGS 432/)).toBeInTheDocument();
    expect(card.queryByRole("link", { name: "IPCA 12 meses" })).not.toBeInTheDocument();

    const ibgeCard = within(
      screen.getByRole("region", { name: "Instituto Brasileiro de Geografia e Estatística (IBGE)" }),
    );
    expect(ibgeCard.getByText("Não informada")).toBeInTheDocument();
    expect(ibgeCard.getByRole("link", { name: "IPCA 12 meses" })).toBeInTheDocument();
    expect(ibgeCard.getByRole("link", { name: "série oficial" })).toHaveAttribute(
      "href",
      "https://sidra.ibge.gov.br/tabela/1737",
    );
  });

  it("says when a source feeds no indicator", async () => {
    routes["/api/v1/indicators"] = () => json([selic]);
    render(<SourcesCatalog />);
    const ibgeCard = await screen.findByRole("region", {
      name: "Instituto Brasileiro de Geografia e Estatística (IBGE)",
    });
    expect(
      await within(ibgeCard).findByText("Nenhum indicador do catálogo usa esta fonte."),
    ).toBeInTheDocument();
  });

  it("keeps the sources visible when only the indicators fail, and retries them", async () => {
    routes["/api/v1/indicators"] = () => json(unavailable, 503);
    render(<SourcesCatalog />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Não foi possível carregar os indicadores de cada fonte.");
    expect(screen.getByRole("region", { name: "Banco Central do Brasil (BCB)" })).toBeInTheDocument();
    expect(screen.queryByText("Indicadores")).not.toBeInTheDocument();

    routes["/api/v1/indicators"] = () => json([selic, ipca]);
    await userEvent.click(within(alert).getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("link", { name: "Meta Selic" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(calls("/api/v1/sources")).toBe(1);
  });

  it("shows an error with retry when the sources fail", async () => {
    routes["/api/v1/sources"] = () => json(unavailable, 503);
    render(<SourcesCatalog />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Banco de dados indisponível.");

    routes["/api/v1/sources"] = () => json([bcb]);
    await userEvent.click(within(alert).getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("region", { name: "Banco Central do Brasil (BCB)" })).toBeInTheDocument();
  });

  it("shows an empty state when no source is registered", async () => {
    routes["/api/v1/sources"] = () => json([]);
    render(<SourcesCatalog />);
    expect(await screen.findByText("Nenhuma fonte cadastrada no catálogo.")).toBeInTheDocument();
  });
});
