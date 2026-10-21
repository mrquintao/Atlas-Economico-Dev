import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { STATES } from "@/lib/states";
import type { Indicator, StateBoundaries, StateDashboard, StateMap, StateMapPeriod } from "@/types/api";

import { SEQUENTIAL_PALETTE } from "./map-scale";
import { DEFAULT_MAP_CODE, DIVERGING_NOTE, StateMapPanel, stateIndicatorOptions } from "./StateMap";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }), usePathname: () => "/estados" }));

// ---- Synthetic API responses (test-only data, not official values) ----

const DF_NOTE = "O Distrito Federal acumula competências estaduais e municipais.";

function indicator(code: string, frequency: Indicator["frequency"], unit: string, first: string): Indicator {
  return {
    code,
    name: `Nome de ${code}`,
    short_name: `Curto ${code}`,
    description: "",
    unit,
    change_unit: unit === "R$ correntes" ? unit : "p.p.",
    frequency,
    geographic_level: "state",
    methodology: "",
    methodology_version: null,
    first_available_date: null,
    source: { acronym: "SICONFI", name: "SICONFI", organization: "STN", base_url: "", documentation_url: null },
    source_series_code: "",
    source_url: "",
    first_stored_date: first,
    last_stored_date: "2025-09-01",
    last_collected_at: null,
    last_run: null,
  };
}

const PERSONNEL = indicator(DEFAULT_MAP_CODE, "four_monthly", "% da RCL ajustada", "2018-01-01");
const DCL_RCL = indicator("STATE_DCL_RCL", "four_monthly", "% da RCL ajustada", "2020-01-01");
const RCL = indicator("STATE_RCL", "bimonthly", "R$ correntes", "2018-01-01");
const CATALOG = [RCL, DCL_RCL, PERSONNEL, indicator("SELIC_TARGET", "daily", "% a.a.", "2000-01-01")];

const Q = (start: string, end: string, coverage: number): StateMapPeriod => ({
  reference_date: start,
  period_start: start,
  period_end: end,
  coverage,
});
const PERIODS = [Q("2025-05-01", "2025-08-31", 3), Q("2025-01-01", "2025-04-30", 26)];

/** Every UF has a value except DF (absent: never zero). */
function mapFor(code: string, referenceDate: string | null): StateMap {
  const ind = CATALOG.find((i) => i.code === code) ?? PERSONNEL;
  const period = PERIODS.find((p) => p.reference_date === referenceDate) ?? PERIODS[1];
  return {
    indicator: ind,
    accumulation_window: "Últimos 12 meses até o fim do período.",
    scale: code === "STATE_DCL_RCL" ? "diverging" : "sequential",
    period,
    default_rule: "Período padrão: o mais recente com pelo menos 14 das 27 UFs.",
    available_periods: PERIODS,
    notes: [DF_NOTE],
    states: STATES.toSorted((a, b) => a.acronym.localeCompare(b.acronym)).map((s, i) => ({
      geography: { ibge_code: s.ibgeCode, acronym: s.acronym, name: s.name, geographic_level: "state" },
      status: s.acronym === "DF" ? "no_data" : "available",
      value: s.acronym === "DF" ? null : code === "STATE_DCL_RCL" ? i - 5 : 30 + i,
    })),
  };
}

const BOUNDARIES: StateBoundaries = {
  type: "FeatureCollection",
  metadata: { source_url: "synthetic", mesh_year: 2022, collected_at: "2026-07-01T09:00:00Z" },
  features: STATES.map((s, i) => {
    const [x, y] = [-72 + 5 * (i % 7), 4 - 5 * Math.floor(i / 7)];
    return {
      type: "Feature",
      id: s.ibgeCode,
      properties: { ibge_code: s.ibgeCode, acronym: s.acronym, name: s.name },
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [x, y],
            [x, y - 4],
            [x + 4, y - 4],
            [x + 4, y],
            [x, y],
          ],
        ],
      },
    };
  }),
};

/** Dashboard of a UF: RCL published, DCL/RCL never stored (absent, not zero). */
function dashboardFor(acronym: string): StateDashboard {
  const state = STATES.find((s) => s.acronym === acronym) ?? STATES[0];
  const none = { method: "none" as const, description: "" };
  return {
    geography: { ibge_code: state.ibgeCode, acronym: state.acronym, name: state.name, geographic_level: "state" },
    notes: acronym === "DF" ? [DF_NOTE] : [],
    indicators: [
      {
        indicator: RCL,
        status: "available",
        aggregation: none,
        accumulation_window: "Últimos 12 meses até o fim do período.",
        change_note: null,
        latest: { date: "2025-11-01", value: 268e9, period_start: "2025-11-01", period_end: "2025-12-31", partial: false },
        change_12m: null,
      },
      {
        indicator: DCL_RCL,
        status: "no_data",
        aggregation: none,
        accumulation_window: "Saldo no fim do período.",
        change_note: null,
        latest: null,
        change_12m: null,
      },
    ],
  };
}

let fetchMock: ReturnType<typeof vi.fn>;
let boundariesStatus = 200;
/** "CODE@date" pairs answered with 404 period_not_found (a gap of that indicator). */
let gaps = new Set<string>();
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

async function defaultFetch(url: string): Promise<Response> {
  const { pathname, searchParams } = new URL(url);
  if (pathname.endsWith("/geographies/states/boundaries")) {
    return boundariesStatus === 200
      ? json(BOUNDARIES)
      : json({ error: { code: "boundaries_not_found", message: "Malha das UFs não coletada." } }, 404);
  }
  if (pathname.endsWith("/indicators")) return json(CATALOG);
  const uf = /\/states\/([A-Z]{2})\/dashboard$/.exec(pathname)?.[1];
  if (uf) return json(dashboardFor(uf));
  const code = /\/states\/map\/([^/]+)$/.exec(pathname)?.[1];
  const date = searchParams.get("reference_date");
  if (code && gaps.has(`${code}@${date}`)) {
    return json({ error: { code: "period_not_found", message: `Nenhuma UF tem valor de '${code}' no período ${date}.` } }, 404);
  }
  if (code) return json(mapFor(code, date));
  return json({ error: { code: "not_found", message: "Rota inesperada." } }, 404);
}

function mapRequests(): URL[] {
  return fetchMock.mock.calls
    .map(([url]) => new URL(String(url)))
    .filter((u) => u.pathname.includes("/states/map/"));
}

async function findState(name: RegExp): Promise<HTMLElement> {
  const map = await screen.findByRole("group", { name: /^Mapa de / });
  return within(map).findByRole("button", { name });
}

beforeEach(() => {
  boundariesStatus = 200;
  gaps = new Set();
  push.mockClear();
  fetchMock = vi.fn(defaultFetch);
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("stateIndicatorOptions", () => {
  it("keeps only state indicators, in the display order", () => {
    expect(stateIndicatorOptions(CATALOG).map((i) => i.code)).toEqual([
      "STATE_RCL",
      DEFAULT_MAP_CODE,
      "STATE_DCL_RCL",
    ]);
  });
});

describe("StateMapPanel", () => {
  it("draws the 27 UFs as toggle buttons named by value, unit and period; DF without data is hatched", async () => {
    render(<StateMapPanel />);
    const map = await screen.findByRole("group", { name: /^Mapa de /, });
    await waitFor(() => expect(within(map).getAllByRole("button")).toHaveLength(27));
    expect(mapRequests()[0].pathname).toBe(`/api/v1/states/map/${DEFAULT_MAP_CODE}`);
    expect(mapRequests()[0].searchParams.has("reference_date")).toBe(false);

    const sp = await findState(/^São Paulo:/);
    expect(sp).toHaveAccessibleName("São Paulo: 55,00% da RCL ajustada, 1º quadr./2025 (jan–abr)");
    expect(sp).toHaveAttribute("aria-pressed", "false");
    expect(sp.getAttribute("fill")).toMatch(/^#/);

    const df = await findState(/^Distrito Federal/);
    expect(df).toHaveAccessibleName("Distrito Federal*: sem dado, 1º quadr./2025 (jan–abr)");
    // Never a palette colour (nor the colour of the lowest class) for a missing value.
    const fill = df.getAttribute("fill") ?? "";
    expect(fill).toMatch(/^url\(#no-data/);
    expect(SEQUENTIAL_PALETTE).not.toContain(fill);
    expect(screen.getByText("26 de 27 UFs com dado publicado neste período.")).toBeInTheDocument();
  });

  it("shows a legend with real ranges, unit, the no-data entry and the notes", async () => {
    render(<StateMapPanel />);
    const legend = await screen.findByRole("list", { name: "Legenda do mapa" });
    const items = within(legend).getAllByRole("listitem");
    expect(items).toHaveLength(6);
    expect(items[0]).toHaveTextContent("30,00% da RCL ajustada a 34,00% da RCL ajustada (5 UFs)");
    expect(items[5]).toHaveTextContent("Sem dado (1 UF)");
    expect(screen.getByRole("heading", { name: "Legenda (% da RCL ajustada)" })).toBeInTheDocument();
    expect(screen.getByText(`* ${DF_NOTE}`)).toBeInTheDocument();
    expect(screen.getByText(/Ausência não é zero/)).toBeInTheDocument();
    expect(screen.queryByText(DIVERGING_NOTE)).not.toBeInTheDocument();
  });

  it("lists every UF in an alternative table, with explicit absences", async () => {
    render(<StateMapPanel />);
    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(28);
    const df = within(table).getByRole("rowheader", { name: "Distrito Federal* (DF)" }).closest("tr");
    expect(df).toHaveTextContent("sem dado");
    expect(df).toHaveTextContent("Sem dado");
    expect(within(table).getByRole("link", { name: "Acre (AC)" })).toHaveAttribute("href", "/estados/AC");
  });

  it("keyboard: Tab focuses a UF and shows its tooltip; Enter selects it, Escape clears", async () => {
    const user = userEvent.setup();
    render(<StateMapPanel />);
    const acre = await findState(/^Acre:/);
    // Links are in alphabetical order: Acre is the first UF of the map.
    const selects = screen.getAllByRole("combobox");
    selects[1].focus();
    await user.tab();
    expect(acre).toHaveFocus();
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent("Acre");
    expect(tooltip).toHaveTextContent("% da RCL ajustada · 1º quadr./2025 (jan–abr)");
    await user.keyboard("{Enter}");
    expect(acre).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByRole("heading", { level: 3, name: "Acre AC" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(acre).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("heading", { level: 3, name: "Nenhuma UF selecionada" })).toBeInTheDocument();
    await user.tab();
    expect(await findState(/^Alagoas:/)).toHaveFocus();
  });

  it("a click selects the UF and shows its map value and latest published values, without navigating", async () => {
    render(<StateMapPanel />);
    const mg = await findState(/^Minas Gerais:/);
    fireEvent.click(mg);
    expect(push).not.toHaveBeenCalled();
    expect(mg).toHaveAttribute("aria-pressed", "true");
    const panel = screen.getByRole("region", { name: "Minas Gerais MG" });
    expect(panel).toHaveTextContent("Região Sudeste");
    expect(panel).toHaveTextContent("Curto STATE_PERSONNEL_EXEC_RCL · 1º quadr./2025 (jan–abr)");
    expect(panel).toHaveTextContent(/4\d,00% da RCL ajustada/);
    expect(panel).toHaveTextContent(/Faixa \d de 5 da legenda/);

    const latest = await within(panel).findByRole("region", { name: "Últimos valores publicados" });
    await waitFor(() => expect(latest).toHaveTextContent("Curto STATE_RCL"));
    expect(latest).toHaveTextContent("6º bim./2025 (nov–dez)");
    expect(latest).toHaveTextContent("R$ 268,00 bi");
    // A missing indicator is named as missing, never shown as zero.
    expect(latest).toHaveTextContent("Sem dados nesta UF: Curto STATE_DCL_RCL.");
    expect(within(panel).getByRole("link", { name: "Abrir o painel completo da UF" })).toHaveAttribute(
      "href",
      "/estados/MG",
    );
    expect(
      fetchMock.mock.calls.some(([url]) => new URL(String(url)).pathname.endsWith("/states/MG/dashboard")),
    ).toBe(true);

    // A second click on the same UF clears the selection.
    fireEvent.click(mg);
    expect(mg).toHaveAttribute("aria-pressed", "false");
  });

  it("a UF without a value in the map says so; the list picker and the clear button work", async () => {
    const user = userEvent.setup();
    render(<StateMapPanel />);
    await findState(/^Distrito Federal/);
    await user.selectOptions(screen.getByRole("combobox", { name: "Ou escolha na lista" }), "DF");
    const panel = screen.getByRole("region", { name: "Distrito Federal* DF" });
    expect(panel).toHaveTextContent("Sem dado");
    expect(panel).toHaveTextContent("Ausência não é zero.");
    expect(await within(panel).findByText(`* ${DF_NOTE}`)).toBeInTheDocument();
    expect(await findState(/^Distrito Federal/)).toHaveAttribute("aria-pressed", "true");

    await user.click(within(panel).getByRole("button", { name: "Limpar seleção" }));
    expect(screen.getByRole("heading", { level: 3, name: "Nenhuma UF selecionada" })).toBeInTheDocument();
  });

  it("the selection survives an indicator change", async () => {
    const user = userEvent.setup();
    render(<StateMapPanel />);
    fireEvent.click(await findState(/^São Paulo:/));
    const select = screen.getByRole("combobox", { name: "Indicador" });
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3));
    await user.selectOptions(select, "STATE_DCL_RCL");
    await screen.findByRole("group", { name: /^Mapa de Curto STATE_DCL_RCL/ });
    const panel = screen.getByRole("region", { name: "São Paulo SP" });
    await waitFor(() => expect(panel).toHaveTextContent("Curto STATE_DCL_RCL · 1º quadr./2025 (jan–abr)"));
    expect(await findState(/^São Paulo:/)).toHaveAttribute("aria-pressed", "true");
  });

  it("hover shows the value, unit and period; a missing UF says so", async () => {
    render(<StateMapPanel />);
    const df = await findState(/^Distrito Federal/);
    fireEvent.mouseMove(df, { clientX: 10, clientY: 10 });
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent("Distrito Federal*");
    expect(tooltip).toHaveTextContent("sem dado");
    expect(tooltip).toHaveTextContent("nenhum valor publicado (não é zero)");
  });

  it("the period filter refetches the map at the chosen period", async () => {
    const user = userEvent.setup();
    render(<StateMapPanel />);
    const period = await screen.findByRole("combobox", { name: "Período" });
    await waitFor(() => expect(period).toHaveValue("2025-01-01"));
    expect(within(period).getByRole("option", { name: "2º quadr./2025 (mai–ago) — 3 UFs" })).toBeInTheDocument();
    await user.selectOptions(period, "2025-05-01");
    await waitFor(() => expect(mapRequests().at(-1)?.searchParams.get("reference_date")).toBe("2025-05-01"));
    await waitFor(() => expect(period).toHaveValue("2025-05-01"));
  });

  it("changing indicator keeps the period of the same kind, otherwise uses the default", async () => {
    const user = userEvent.setup();
    render(<StateMapPanel />);
    const select = await screen.findByRole("combobox", { name: "Indicador" });
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3));
    await user.selectOptions(screen.getByRole("combobox", { name: "Período" }), "2025-05-01");
    await waitFor(() => expect(mapRequests()).toHaveLength(2));

    await user.selectOptions(select, "STATE_DCL_RCL");
    await waitFor(() => expect(mapRequests().at(-1)?.pathname).toMatch(/STATE_DCL_RCL$/));
    expect(mapRequests().at(-1)?.searchParams.get("reference_date")).toBe("2025-05-01");
    expect(await screen.findByText(DIVERGING_NOTE)).toBeInTheDocument();

    // Four-monthly → bimonthly: a different kind of period, back to the default.
    await user.selectOptions(select, "STATE_RCL");
    await waitFor(() => expect(mapRequests().at(-1)?.pathname).toMatch(/STATE_RCL$/));
    expect(mapRequests().at(-1)?.searchParams.has("reference_date")).toBe(false);
  });

  it("a kept period that is a gap of the new indicator: no stale map, offers the default", async () => {
    gaps = new Set(["STATE_DCL_RCL@2025-05-01"]);
    const user = userEvent.setup();
    render(<StateMapPanel />);
    const select = await screen.findByRole("combobox", { name: "Indicador" });
    await waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3));
    await user.selectOptions(screen.getByRole("combobox", { name: "Período" }), "2025-05-01");
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Período" })).toHaveValue("2025-05-01"));

    await user.selectOptions(select, "STATE_DCL_RCL");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Nenhuma UF tem valor de 'STATE_DCL_RCL' no período 2025-05-01.");
    // The previous indicator's map, legend and table are not left under the error.
    expect(screen.queryByRole("group", { name: /^Mapa de / })).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();

    await user.click(within(alert).getByRole("button", { name: "Ver o período padrão" }));
    await waitFor(() => expect(mapRequests().at(-1)?.searchParams.has("reference_date")).toBe(false));
    expect(await screen.findByRole("group", { name: /^Mapa de Curto STATE_DCL_RCL/ })).toBeInTheDocument();
  });

  it("without the official boundaries, says so and keeps the table", async () => {
    boundariesStatus = 404;
    render(<StateMapPanel />);
    expect(await screen.findByText(/malha oficial das UFs \(IBGE\) ainda não foi coletada/)).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: /^Mapa de / })).not.toBeInTheDocument();
  });
});
