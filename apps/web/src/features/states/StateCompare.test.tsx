import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Geography, Indicator, Observation, StateComparison, StateRanking } from "@/types/api";

import { COMPARISON_COLORS } from "./comparison-option";
import { DEFAULT_COMPARISON_UFS, MAX_COMPARISON_UFS, StateComparisonPanel } from "./StateComparison";
import { DEFAULT_RANKING_CODE, StateRankingPanel } from "./StateRanking";

// ECharts needs a real canvas; the option is covered by comparison-option tests.
const setOption = vi.fn();
vi.mock("echarts/core", () => ({
  use: vi.fn(),
  init: () => ({ setOption, resize: vi.fn(), dispose: vi.fn() }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), usePathname: () => "/estados/comparar" }));

// ---- Synthetic API responses (test-only data, not official values) ----

const DF_NOTE = "O Distrito Federal acumula competências estaduais e municipais.";
const geo = (acronym: string, name: string, ibge_code: string): Geography => ({
  acronym,
  name,
  ibge_code,
  geographic_level: "state",
});
const SP = geo("SP", "São Paulo", "35");
const MG = geo("MG", "Minas Gerais", "31");
const DF = geo("DF", "Distrito Federal", "53");
const RJ = geo("RJ", "Rio de Janeiro", "33");

function indicator(code: string, unit: string): Indicator {
  return {
    code,
    name: `Nome de ${code}`,
    short_name: `Curto ${code}`,
    description: "",
    unit,
    change_unit: unit === "R$ correntes" ? unit : "p.p.",
    frequency: "four_monthly",
    geographic_level: "state",
    methodology: "",
    methodology_version: null,
    first_available_date: null,
    source: { acronym: "SICONFI", name: "SICONFI", organization: "STN", base_url: "", documentation_url: null },
    source_series_code: "",
    source_url: "",
    first_stored_date: "2020-01-01",
    last_stored_date: "2025-09-01",
    last_collected_at: null,
    last_run: null,
  };
}

const DCL_RCL = indicator(DEFAULT_RANKING_CODE, "% da RCL ajustada");
const PERSONNEL_RCL = indicator("STATE_PERSONNEL_EXEC_RCL", "% da RCL ajustada");
const DC = indicator("STATE_DC", "R$ correntes");
const CATALOG = [DC, PERSONNEL_RCL, DCL_RCL];
const PERIOD = { reference_date: "2025-01-01", period_start: "2025-01-01", period_end: "2025-04-30", coverage: 3 };

function rankingFor(code: string, ufs: string | null, order: string | null): StateRanking {
  const ind = CATALOG.find((i) => i.code === code) ?? DCL_RCL;
  const absolute = ind.unit === "R$ correntes";
  const ranking = [
    { position: 1, geography: MG, value: 167.46 },
    { position: 2, geography: SP, value: 124.23 },
    { position: 2, geography: RJ, value: 124.23 },
    { position: 4, geography: DF, value: -3.5 },
  ];
  return {
    indicator: ind,
    accumulation_window: "Saldo no fim do quadrimestre.",
    metric_kind: absolute ? "absolute" : "relative",
    order: order === "asc" ? "asc" : "desc",
    order_note: order === "asc" ? "Do menor para o maior." : "Do maior para o menor. A posição não indica desempenho melhor ou pior.",
    period: PERIOD,
    default_rule: "Período padrão: regra.",
    available_periods: [PERIOD],
    selected_count: ufs ? ufs.split(",").length : 27,
    ranked_count: 4,
    ranking: order === "asc" ? ranking.toReversed() : ranking,
    missing: [geo("AC", "Acre", "12")],
    missing_note: "Sem dado no período: AC. Ausência de dado não equivale a zero.",
    notes: absolute ? ["Valores absolutos: a ordem reflete sobretudo o tamanho.", DF_NOTE] : ["Métrica relativa.", DF_NOTE],
  };
}

const obs = (date: string, value: number): Observation => ({
  date,
  value,
  period_start: date,
  period_end: date,
  partial: false,
});

function comparisonFor(code: string, ufs: string[]): StateComparison {
  const ind = CATALOG.find((i) => i.code === code) ?? DCL_RCL;
  const byUf: Record<string, Geography> = { SP, MG, RJ, DF };
  return {
    indicator: ind,
    accumulation_window: "Saldo no fim do quadrimestre.",
    start_date: null,
    end_date: null,
    notes: ["Cada linha mostra a série da UF como publicada."],
    series: ufs.map((uf) => ({
      indicator: ind,
      geography: byUf[uf] ?? geo(uf, uf, "00"),
      unit: ind.unit,
      original_frequency: "four_monthly",
      frequency: "four_monthly",
      aggregation: { method: "none", description: "" },
      start_date: null,
      end_date: null,
      count: uf === "RJ" ? 0 : 2,
      stats: null,
      observations: uf === "RJ" ? [] : [obs("2024-09-01", 100), obs("2025-01-01", 110)],
      status: uf === "RJ" ? "no_data" : "available",
      accumulation_window: "Saldo no fim do quadrimestre.",
    })),
  };
}

let fetchMock: ReturnType<typeof vi.fn>;
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

async function defaultFetch(url: string): Promise<Response> {
  const { pathname, searchParams } = new URL(url);
  if (pathname.endsWith("/indicators")) return json(CATALOG);
  const ranking = /\/states\/ranking\/([^/]+)$/.exec(pathname)?.[1];
  if (ranking) return json(rankingFor(ranking, searchParams.get("ufs"), searchParams.get("order")));
  const compare = /\/states\/compare\/([^/]+)$/.exec(pathname)?.[1];
  if (compare) return json(comparisonFor(compare, (searchParams.get("ufs") ?? "").split(",")));
  return json({ error: { code: "not_found", message: "Rota inesperada." } }, 404);
}

function requests(path: string): URL[] {
  return fetchMock.mock.calls.map(([url]) => new URL(String(url))).filter((u) => u.pathname.includes(path));
}

beforeEach(() => {
  setOption.mockClear();
  fetchMock = vi.fn(defaultFetch);
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("StateRankingPanel", () => {
  it("ranks every UF by the default relative metric, ties sharing a position", async () => {
    render(<StateRankingPanel />);
    const table = await screen.findByRole("table", { name: /^Ranking de Nome de STATE_DCL_RCL/ });
    expect(requests("/states/ranking/")[0].pathname).toBe(`/api/v1/states/ranking/${DEFAULT_RANKING_CODE}`);
    expect(requests("/states/ranking/")[0].search).toBe("");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual([
      "1ºMinas Gerais (MG)167,46% da RCL ajustada",
      "2ºSão Paulo (SP)124,23% da RCL ajustada",
      "2ºRio de Janeiro (RJ)124,23% da RCL ajustada",
      "4ºDistrito Federal* (DF)-3,50% da RCL ajustada",
    ]);
    expect(within(table).getByRole("link", { name: "Minas Gerais (MG)" })).toHaveAttribute("href", "/estados/MG");
    expect(screen.getByText("4 de 27 UFs selecionadas com dado publicado neste período.")).toBeInTheDocument();
    expect(screen.getByText(/Sem dado no período: AC/)).toBeInTheDocument();
    expect(screen.getByText(/não indica desempenho/)).toBeInTheDocument();
    expect(screen.getByText(`* ${DF_NOTE}`)).toBeInTheDocument();
    expect(screen.queryByText(/a ordem reflete sobretudo o tamanho de cada UF/)).not.toBeInTheDocument();
  });

  it("offers relative metrics first and warns about absolute values", async () => {
    const user = userEvent.setup();
    render(<StateRankingPanel />);
    const select = await screen.findByRole("combobox", { name: "Indicador" });
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3));
    const groups = within(select).getAllByRole("group");
    expect(groups.map((g) => g.getAttribute("label"))).toEqual([
      "Métricas relativas (recomendadas)",
      "Valores absolutos (refletem o porte da UF)",
    ]);
    expect(within(groups[0]).getAllByRole("option").map((o) => o.getAttribute("value"))).toEqual([
      "STATE_PERSONNEL_EXEC_RCL",
      "STATE_DCL_RCL",
    ]);
    await user.selectOptions(select, "STATE_DC");
    expect(await screen.findByText("Valor absoluto: a ordem reflete sobretudo o tamanho de cada UF.")).toBeInTheDocument();
    // Same kind of period and within the stored range: the period is kept.
    expect(requests("/states/ranking/").at(-1)?.searchParams.get("reference_date")).toBe("2025-01-01");
  });

  it("sends the selected UFs and order; fewer than two UFs keep the previous selection", async () => {
    const user = userEvent.setup();
    render(<StateRankingPanel />);
    await screen.findByRole("table");
    await user.click(screen.getByRole("button", { name: "Menor → maior" }));
    await waitFor(() => expect(requests("/states/ranking/").at(-1)?.searchParams.get("order")).toBe("asc"));

    await user.click(screen.getByText(/^UFs selecionadas/));
    await user.click(screen.getByRole("button", { name: "Nenhuma" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Selecione ao menos 2 UFs");
    const before = requests("/states/ranking/").length;
    await user.click(screen.getByRole("checkbox", { name: "SP (São Paulo)" }));
    expect(requests("/states/ranking/")).toHaveLength(before);
    await user.click(screen.getByRole("checkbox", { name: "MG (Minas Gerais)" }));
    await waitFor(() => expect(requests("/states/ranking/").at(-1)?.searchParams.get("ufs")).toBe("MG,SP"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("StateRankingPanel errors", () => {
  it("never shows the previous ranking under a failed request", async () => {
    const user = userEvent.setup();
    render(<StateRankingPanel />);
    await screen.findByRole("table");
    fetchMock.mockImplementation(async (url: string) =>
      url.includes("/states/ranking/")
        ? json({ error: { code: "internal", message: "Falha na API." } }, 500)
        : defaultFetch(url),
    );
    await user.click(screen.getByRole("button", { name: "Menor → maior" }));
    expect(await screen.findByText("Falha na API.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    fetchMock.mockImplementation(defaultFetch);
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByRole("table")).toBeInTheDocument();
  });

  it("offers the default period when the chosen one has no value", async () => {
    const user = userEvent.setup();
    render(<StateRankingPanel />);
    await screen.findByRole("table");
    fetchMock.mockImplementation(async (url: string) =>
      new URL(url).searchParams.has("reference_date")
        ? json({ error: { code: "period_not_found", message: "Nenhuma UF tem valor neste período." } }, 404)
        : defaultFetch(url),
    );
    await user.selectOptions(screen.getByRole("combobox", { name: "Indicador" }), "STATE_DC");
    expect(await screen.findByText("Nenhuma UF tem valor neste período.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ver o período padrão" }));
    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect(requests("/states/ranking/").at(-1)?.searchParams.has("reference_date")).toBe(false);
  });
});

describe("StateComparisonPanel", () => {
  it("plots the selected UFs and lists those without data apart", async () => {
    render(<StateComparisonPanel />);
    const chart = await screen.findByRole("img", { name: /^Curto STATE_DCL_RCL por UF\./ });
    expect(requests("/states/compare/")[0].searchParams.get("ufs")).toBe(DEFAULT_COMPARISON_UFS.join(","));
    expect(chart).toHaveAccessibleName(
      "Curto STATE_DCL_RCL por UF. SP: 2 valores de 3º quadr./2024 a 1º quadr./2025, o último 110,00% da RCL ajustada; MG: 2 valores de 3º quadr./2024 a 1º quadr./2025, o último 110,00% da RCL ajustada; RJ: sem dado.",
    );
    expect(screen.getByText(/^Sem dado: Rio de Janeiro\./)).toHaveTextContent("ausência de dado não equivale a zero");
    await waitFor(() => expect(setOption).toHaveBeenCalled());
    const option = setOption.mock.calls.at(-1)?.[0] as { series: { name: string }[] };
    expect(option.series.map((s) => s.name)).toEqual(["SP", "MG"]);

    // Alternative table: one column per UF, absences written out.
    const table = screen.getByRole("table", { hidden: true });
    const rows = within(table).getAllByRole("row", { hidden: true });
    expect(rows.map((r) => r.textContent)).toEqual([
      "PeríodoSPMGRJ",
      "1º quadr./2025 (jan–abr)110,00% da RCL ajustada110,00% da RCL ajustadasem dado",
      "3º quadr./2024 (set–dez)100,00% da RCL ajustada100,00% da RCL ajustadasem dado",
    ]);
  });

  it("keeps colours by selection order and marks the DF", async () => {
    const user = userEvent.setup();
    render(<StateComparisonPanel />);
    await screen.findByRole("img", { name: /por UF\./ });
    await user.click(screen.getByRole("checkbox", { name: "DF (Distrito Federal)" }));
    await waitFor(() =>
      expect(requests("/states/compare/").at(-1)?.searchParams.get("ufs")).toBe("SP,MG,RJ,DF"),
    );
    await waitFor(() => {
      const option = setOption.mock.calls.at(-1)?.[0] as { series: { name: string; color: string }[] };
      // RJ (3rd) has no data: DF keeps the 4th colour.
      expect(option.series.map((s) => [s.name, s.color])).toEqual([
        ["SP", COMPARISON_COLORS[0]],
        ["MG", COMPARISON_COLORS[1]],
        ["DF*", COMPARISON_COLORS[3]],
      ]);
    });
  });

  it("never plots the previous UFs under a failed request", async () => {
    const user = userEvent.setup();
    render(<StateComparisonPanel />);
    await screen.findByRole("img", { name: /por UF\./ });
    fetchMock.mockImplementation(async (url: string) =>
      url.includes("/states/compare/")
        ? json({ error: { code: "internal", message: "Falha na API." } }, 500)
        : defaultFetch(url),
    );
    await user.click(screen.getByRole("checkbox", { name: "BA (Bahia)" }));
    expect(await screen.findByText("Falha na API.")).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /por UF\./ })).not.toBeInTheDocument();
  });

  it("limits the selection to six UFs", async () => {
    const user = userEvent.setup();
    render(<StateComparisonPanel />);
    await screen.findByRole("img", { name: /por UF\./ });
    for (const name of ["BA (Bahia)", "PR (Paraná)", "CE (Ceará)"]) {
      await user.click(screen.getByRole("checkbox", { name }));
    }
    expect(screen.getAllByRole("checkbox", { checked: true })).toHaveLength(MAX_COMPARISON_UFS);
    expect(screen.getByRole("checkbox", { name: "GO (Goiás)" })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: "BA (Bahia)" })).toBeEnabled();
    await waitFor(() =>
      expect(requests("/states/compare/").at(-1)?.searchParams.get("ufs")).toBe("SP,MG,RJ,BA,PR,CE"),
    );
  });
});
