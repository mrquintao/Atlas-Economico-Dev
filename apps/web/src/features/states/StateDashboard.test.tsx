import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  Indicator,
  Observation,
  StateDashboard as StateDashboardResponse,
  StateDashboardItem,
  StateIndicatorSeries,
  StateIndicators,
} from "@/types/api";

import { StateDashboard, stateBounds } from "./StateDashboard";

// ECharts needs a real canvas; the chart itself is covered by chart-option tests.
vi.mock("../dashboard/TimeSeriesChart", () => ({
  TimeSeriesChart: (props: {
    name: string;
    observations: Observation[];
    summary: string;
    resetsEachYear?: boolean;
    domain: { min: string; max: string } | null;
  }) => (
    <div
      data-testid={`chart-${props.name}`}
      data-points={props.observations.length}
      data-resets={String(Boolean(props.resetsEachYear))}
      data-domain={props.domain ? `${props.domain.min}/${props.domain.max}` : ""}
    >
      {props.summary}
    </div>
  ),
}));

// ---- Synthetic API responses (test-only data, not official values) ----

const SP = { ibge_code: "35", acronym: "SP", name: "São Paulo", geographic_level: "state" };
const DF = { ibge_code: "53", acronym: "DF", name: "Distrito Federal", geographic_level: "state" };
const MG = { ibge_code: "31", acronym: "MG", name: "Minas Gerais", geographic_level: "state" };
const DF_NOTE = "O Distrito Federal acumula competências estaduais e municipais.";
const TRAILING = "Últimos 12 meses até o fim do período.";
const YTD = "Acumulado no ano até o bimestre (recomeça em janeiro).";
const CHANGE_NOTE_BRL =
  "Diferença em relação ao mesmo período do ano anterior, em reais correntes, sem correção pela inflação.";

const base: Indicator = {
  code: "STATE_RCL",
  name: "Receita corrente líquida (RCL) dos estados - últimos 12 meses",
  short_name: "Receita corrente líquida",
  description: "Receitas correntes do estado, somadas nos 12 meses.",
  unit: "R$ correntes",
  change_unit: "R$ correntes",
  frequency: "bimonthly",
  geographic_level: "state",
  methodology: "RREO Anexo 3.",
  methodology_version: null,
  first_available_date: "2018-01-01",
  source: {
    acronym: "SICONFI",
    name: "SICONFI",
    organization: "Secretaria do Tesouro Nacional",
    base_url: "https://apidatalake.tesouro.gov.br/ords/siconfi/tt",
    documentation_url: null,
  },
  source_series_code: "RREO-Anexo 03 · RREO3ReceitaCorrenteLiquida",
  source_url: "https://siconfi.tesouro.gov.br",
  first_stored_date: "2024-01-01",
  last_stored_date: "2025-11-01",
  last_collected_at: "2026-10-01T12:00:00Z",
  last_run: null,
};

const rcl = base;
const primary: Indicator = {
  ...base,
  code: "STATE_PRIMARY_RESULT",
  name: "Resultado primário dos estados",
  short_name: "Resultado primário",
  description: "Resultado primário acumulado no ano.",
};
const dclRcl: Indicator = {
  ...base,
  code: "STATE_DCL_RCL",
  name: "DCL em % da RCL ajustada",
  short_name: "DCL / RCL",
  description: "Dívida consolidada líquida sobre a RCL ajustada.",
  unit: "% da RCL ajustada",
  change_unit: "p.p.",
  frequency: "four_monthly",
  source_series_code: "RGF-Anexo 02 · PercentualDaDCLSobreARCL",
  last_stored_date: "2025-09-01",
};
const dc: Indicator = {
  ...base,
  code: "STATE_DC",
  name: "Dívida consolidada",
  short_name: "Dívida consolidada",
  frequency: "four_monthly",
};
const ALL = [rcl, primary, dclRcl, dc];

function obs(start: string, end: string, value: number): Observation {
  return { date: start, value, period_start: start, period_end: end, partial: false };
}

const SERIES: Record<string, Observation[]> = {
  STATE_RCL: [obs("2024-11-01", "2024-12-31", 255.1e9), obs("2025-11-01", "2025-12-31", 266.22e9)],
  STATE_PRIMARY_RESULT: [obs("2024-11-01", "2024-12-31", 9e9), obs("2025-01-01", "2025-02-28", 2e9)],
  STATE_DCL_RCL: [obs("2025-09-01", "2025-12-31", 112.4)],
};

function noData(indicator: Indicator): Indicator {
  return { ...indicator, first_stored_date: null, last_stored_date: null, last_collected_at: null };
}

function seriesItem(indicator: Indicator, available: boolean): StateIndicatorSeries {
  const observations = available ? (SERIES[indicator.code] ?? []) : [];
  const first = observations[0];
  const last = observations.at(-1);
  const ytd = indicator.code === "STATE_PRIMARY_RESULT";
  return {
    indicator: available ? indicator : noData(indicator),
    geography: SP,
    unit: indicator.unit,
    original_frequency: indicator.frequency,
    frequency: indicator.frequency,
    aggregation: { method: "none", description: "Valores na frequência original." },
    start_date: null,
    end_date: null,
    count: observations.length,
    stats:
      first && last && !ytd
        ? {
            first: { date: first.date, value: first.value },
            last: { date: last.date, value: last.value },
            change: last.value - first.value,
            change_unit: indicator.change_unit,
            min: { date: first.date, value: first.value },
            max: { date: last.date, value: last.value },
          }
        : null,
    observations,
    status: available ? "available" : "no_data",
    accumulation_window: ytd ? YTD : TRAILING,
  };
}

function dashboardItem(indicator: Indicator, available: boolean): StateDashboardItem {
  const observations = available ? (SERIES[indicator.code] ?? []) : [];
  const last = observations.at(-1);
  const yearAgo = indicator.code === "STATE_RCL" ? observations[0] : undefined;
  return {
    indicator: available ? indicator : noData(indicator),
    status: available ? "available" : "no_data",
    aggregation: { method: "none", description: "Valores na frequência original." },
    latest: last
      ? { date: last.date, value: last.value, period_start: last.period_start, period_end: last.period_end, partial: false }
      : null,
    change_12m:
      last && yearAgo
        ? {
            value: last.value - yearAgo.value,
            change_unit: indicator.change_unit,
            reference_date: yearAgo.date,
            reference_value: yearAgo.value,
          }
        : null,
    accumulation_window: indicator.code === "STATE_PRIMARY_RESULT" ? YTD : TRAILING,
    change_note: last && yearAgo ? CHANGE_NOTE_BRL : null,
  };
}

/** SP and DF have RCL, primary result and DCL/RCL; DC is missing; MG has nothing. */
function availableIn(uf: string, indicator: Indicator): boolean {
  return uf !== "MG" && indicator.code !== "STATE_DC";
}

function geographyOf(uf: string) {
  return uf === "DF" ? DF : uf === "MG" ? MG : SP;
}

function dashboardFor(uf: string): StateDashboardResponse {
  return {
    geography: geographyOf(uf),
    notes: uf === "DF" ? [DF_NOTE] : [],
    indicators: ALL.map((i) => dashboardItem(i, availableIn(uf, i))),
  };
}

function indicatorsFor(uf: string, start: string | null): StateIndicators {
  return {
    geography: geographyOf(uf),
    start_date: start,
    end_date: null,
    notes: uf === "DF" ? [DF_NOTE] : [],
    indicators: ALL.map((i) => seriesItem(i, availableIn(uf, i))),
  };
}

let fetchMock: ReturnType<typeof vi.fn>;
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

async function defaultFetch(url: string): Promise<Response> {
  const { pathname, searchParams } = new URL(url);
  const uf = /\/states\/([^/]+)\//.exec(pathname)?.[1] ?? "";
  if (pathname.endsWith("/dashboard")) return json(dashboardFor(uf));
  if (pathname.endsWith("/indicators")) return json(indicatorsFor(uf, searchParams.get("start_date")));
  return json({ error: { code: "not_found", message: "Rota inesperada." } }, 404);
}

function requests(suffix: string): URL[] {
  return fetchMock.mock.calls
    .map(([url]) => new URL(String(url)))
    .filter((u) => u.pathname.endsWith(suffix));
}

async function findCard(name: string): Promise<HTMLElement> {
  const highlights = await screen.findByRole("region", { name: "Últimos valores publicados" });
  return within(highlights).findByRole("region", { name });
}

beforeEach(() => {
  fetchMock = vi.fn(defaultFetch);
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("StateDashboard", () => {
  it("shows the latest RCL in reais with its bimester, window and same-period comparison", async () => {
    render(<StateDashboard uf="SP" />);
    const card = await findCard("Receita corrente líquida");
    expect(within(card).getByText("R$ 266,22 bi")).toBeInTheDocument();
    expect(within(card).getByText("6º bim./2025 (nov–dez)")).toBeInTheDocument();
    expect(within(card).getByText(TRAILING)).toBeInTheDocument();
    expect(within(card).getByText("+R$ 11,12 bi")).toBeInTheDocument();
    expect(within(card).getByText(/em relação ao 6º bim\./)).toHaveTextContent(
      "em relação ao 6º bim./2024 (R$ 255,10 bi)",
    );
    expect(within(card).getByText(CHANGE_NOTE_BRL)).toBeInTheDocument();
    expect(
      within(card).getByRole("link", {
        name: "Secretaria do Tesouro Nacional — SICONFI, RREO-Anexo 03 · RREO3ReceitaCorrenteLiquida",
      }),
    ).toHaveAttribute("href", rcl.source_url);
  });

  it("states the sign convention of the fiscal results, only on their cards", async () => {
    render(<StateDashboard uf="SP" />);
    const result = await findCard("Resultado primário");
    expect(within(result).getByText("Positivo indica superávit; negativo, déficit.")).toBeInTheDocument();
    const rclCard = await findCard("Receita corrente líquida");
    expect(within(rclCard).queryByText(/superávit/)).not.toBeInTheDocument();
  });

  it("says when there is no same-period value to compare, never inventing a change", async () => {
    render(<StateDashboard uf="SP" />);
    const card = await findCard("DCL / RCL");
    expect(within(card).getByText("112,40% da RCL ajustada")).toBeInTheDocument();
    expect(within(card).getByText("3º quadr./2025 (set–dez)")).toBeInTheDocument();
    expect(within(card).getByText(/Não há valor armazenado para o mesmo período do ano anterior/)).toBeInTheDocument();
    expect(within(card).queryByText(/p\.p\./)).not.toBeInTheDocument();
  });

  it("lists indicators without data explicitly, with no card and no chart", async () => {
    render(<StateDashboard uf="SP" />);
    const missing = await screen.findByRole("region", { name: "Indicadores sem dados nesta UF" });
    expect(within(missing).getByRole("listitem")).toHaveTextContent("Dívida consolidada");
    expect(within(missing).getByText(/não são estimados nem exibidos como zero/)).toBeInTheDocument();
    await findCard("Receita corrente líquida");
    expect(screen.queryByRole("region", { name: "Dívida consolidada" })).not.toBeInTheDocument();
    expect(await screen.findByTestId("chart-Receita corrente líquida")).toBeInTheDocument();
    expect(screen.queryByTestId("chart-Dívida consolidada")).not.toBeInTheDocument();
  });

  it("draws one panel per available indicator, breaking year-to-date flows at each year", async () => {
    render(<StateDashboard uf="SP" />);
    const rclChart = await screen.findByTestId("chart-Receita corrente líquida");
    expect(rclChart).toHaveAttribute("data-resets", "false");
    expect(rclChart).toHaveTextContent("de 6º bim./2024 a 6º bim./2025");
    // Shared x-axis domain: the UF's earliest first and latest last stored dates.
    expect(rclChart).toHaveAttribute("data-domain", "2024-01-01/2025-11-01");
    const primaryChart = screen.getByTestId("chart-Resultado primário");
    expect(primaryChart).toHaveAttribute("data-resets", "true");
    // No statistics for year-to-date flows (periods not comparable): only the last value.
    expect(primaryChart).toHaveTextContent("2 valores publicados; o último é R$ 2,00 bi.");
    const panel = screen.getByRole("region", { name: primary.name });
    expect(within(panel).queryByText(/Diferença no período/)).not.toBeInTheDocument();
    expect(within(panel).getByText(YTD)).toBeInTheDocument();
    // Amounts in current reais: a difference, labelled with its unit (it includes inflation).
    const rclPanel = within(screen.getByRole("region", { name: rcl.name }));
    expect(rclPanel.getByText("Diferença no período (R$ correntes)")).toBeInTheDocument();
    expect(rclPanel.getByText("Mínima / máxima (R$ correntes)")).toBeInTheDocument();
  });

  it("loads cards and series in one request each and refetches the series for a new period", async () => {
    render(<StateDashboard uf="SP" />);
    await screen.findByTestId("chart-Receita corrente líquida");
    expect(requests("/states/SP/dashboard")).toHaveLength(1);
    expect(requests("/states/SP/indicators")).toHaveLength(1);
    expect(requests("/states/SP/indicators")[0].searchParams.get("start_date")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "5 anos" }));
    // "5 anos" ends at the latest period stored for the UF (nov/2025).
    await waitFor(() =>
      expect(requests("/states/SP/indicators").at(-1)?.searchParams.get("start_date")).toBe("2020-11-01"),
    );
    expect(requests("/states/SP/dashboard")).toHaveLength(1);
  });

  it("shows the Distrito Federal comparability note", async () => {
    render(<StateDashboard uf="DF" />);
    const note = await screen.findByRole("complementary", { name: "Ressalva de comparabilidade" });
    expect(note).toHaveTextContent(DF_NOTE);
  });

  it("has no note for a state", async () => {
    render(<StateDashboard uf="SP" />);
    await findCard("Receita corrente líquida");
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
  });

  it("says plainly when a UF has no fiscal data at all", async () => {
    render(<StateDashboard uf="MG" />);
    expect(
      await screen.findByText(/Ainda não há dados fiscais armazenados para esta UF/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Período predefinido" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: /Indicadores sem dados/ })).not.toBeInTheDocument();
    expect(screen.queryByTestId(/^chart-/)).not.toBeInTheDocument();
  });

  it("offers a retry when the API fails", async () => {
    fetchMock.mockImplementation(async () =>
      json({ error: { code: "boom", message: "Falha simulada." } }, 500),
    );
    render(<StateDashboard uf="SP" />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Não foi possível carregar os dados.")).toBeInTheDocument();

    fetchMock.mockImplementation(defaultFetch);
    for (const button of screen.getAllByRole("button", { name: "Tentar novamente" })) {
      await userEvent.click(button);
    }
    expect(await findCard("Receita corrente líquida")).toBeInTheDocument();
    expect(await screen.findByTestId("chart-Receita corrente líquida")).toBeInTheDocument();
  });
});

describe("stateBounds", () => {
  it("spans the UF's stored dates and ignores indicators without data", () => {
    expect(stateBounds([rcl, dclRcl, noData(dc)])).toEqual({ first: "2024-01-01", last: "2025-11-01" });
    expect(stateBounds([noData(dc)])).toEqual({ first: null, last: null });
  });
});
