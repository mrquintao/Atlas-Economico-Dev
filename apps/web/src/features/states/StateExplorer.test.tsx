import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { STATES } from "@/lib/states";
import type { Indicator, StateBoundaries, StateDashboard } from "@/types/api";

import { StateExplorer } from "./StateExplorer";

// ---- Synthetic API responses (test-only data, not official values) ----

const RCL: Indicator = {
  code: "STATE_RCL",
  name: "Receita corrente líquida",
  short_name: "Receita corrente líquida",
  description: "",
  unit: "R$ correntes",
  change_unit: "R$ correntes",
  frequency: "bimonthly",
  geographic_level: "state",
  methodology: "",
  methodology_version: null,
  first_available_date: null,
  source: { acronym: "SICONFI", name: "SICONFI", organization: "STN", base_url: "", documentation_url: null },
  source_series_code: "",
  source_url: "",
  first_stored_date: "2023-01-01",
  last_stored_date: "2025-11-01",
  last_collected_at: null,
  last_run: null,
};

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

function dashboardFor(acronym: string): StateDashboard {
  const state = STATES.find((s) => s.acronym === acronym) ?? STATES[0];
  return {
    geography: { ibge_code: state.ibgeCode, acronym: state.acronym, name: state.name, geographic_level: "state" },
    notes: [],
    indicators: [
      {
        indicator: RCL,
        status: "available",
        aggregation: { method: "none", description: "" },
        accumulation_window: "Últimos 12 meses até o fim do período.",
        change_note: null,
        latest: { date: "2025-11-01", value: 134e9, period_start: "2025-11-01", period_end: "2025-12-31", partial: false },
        change_12m: null,
      },
    ],
  };
}

let fetchMock: ReturnType<typeof vi.fn>;
let boundariesStatus = 200;
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

async function defaultFetch(url: string): Promise<Response> {
  const { pathname } = new URL(url);
  if (pathname.endsWith("/geographies/states/boundaries")) {
    return boundariesStatus === 200
      ? json(BOUNDARIES)
      : json({ error: { code: "boundaries_not_found", message: "Malha das UFs não coletada." } }, 404);
  }
  const uf = /\/states\/([A-Z]{2})\/dashboard$/.exec(pathname)?.[1];
  if (uf) return json(dashboardFor(uf));
  return json({ error: { code: "not_found", message: "Rota inesperada." } }, 404);
}

async function mapButton(name: string): Promise<HTMLElement> {
  const map = await screen.findByRole("group", { name: "Mapa do Brasil: escolha uma UF" });
  return within(map).findByRole("button", { name });
}

beforeEach(() => {
  boundariesStatus = 200;
  fetchMock = vi.fn(defaultFetch);
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("StateExplorer", () => {
  it("draws the 27 UFs in one neutral colour, named by the UF only, with the explore hint", async () => {
    render(<StateExplorer />);
    const map = await screen.findByRole("group", { name: "Mapa do Brasil: escolha uma UF" });
    await waitFor(() => expect(within(map).getAllByRole("button")).toHaveLength(27));
    // No data is encoded in the fill: every UF shares the same class and has no fill attribute.
    const fills = within(map).getAllByRole("button").map((b) => b.getAttribute("fill"));
    expect(new Set(fills)).toEqual(new Set([null]));
    expect(screen.getByText("Explore o mapa", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Explore o mapa" })).toBeInTheDocument();
    // The map itself never asks for indicator data.
    expect(fetchMock.mock.calls.every(([url]) => !String(url).includes("/states/map/"))).toBe(true);
  });

  it("hover shows the UF name; a click opens its profile with the latest published values", async () => {
    render(<StateExplorer />);
    const mg = await mapButton("Minas Gerais");
    fireEvent.mouseMove(mg, { clientX: 10, clientY: 10 });
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Minas Gerais MG");

    fireEvent.click(mg);
    expect(mg).toHaveAttribute("aria-pressed", "true");
    const profile = screen.getByRole("region", { name: "Minas Gerais MG" });
    expect(profile).toHaveTextContent("Região Sudeste");
    expect(profile).toHaveTextContent("Código IBGE 31");
    const latest = await within(profile).findByRole("region", { name: "Últimos valores publicados" });
    await waitFor(() => expect(latest).toHaveTextContent("R$ 134,00 bi"));
    expect(latest).toHaveTextContent("6º bim./2025 (nov–dez)");
    expect(latest).toHaveTextContent("Últimos 12 meses até o fim do período.");
    expect(within(profile).getByRole("link", { name: "Abrir o painel completo da UF" })).toHaveAttribute(
      "href",
      "/estados/MG",
    );
    expect(screen.queryByText("Explore o mapa", { selector: "p" })).not.toBeInTheDocument();

    fireEvent.click(mg);
    expect(mg).toHaveAttribute("aria-pressed", "false");
  });

  it("keyboard: Enter selects, Escape clears; the clear button keeps focus in the panel", async () => {
    const user = userEvent.setup();
    render(<StateExplorer />);
    const acre = await mapButton("Acre");
    acre.focus();
    await user.keyboard("{Enter}");
    expect(acre).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByText("Acre selecionada.")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(acre).toHaveAttribute("aria-pressed", "false");

    const shortcuts = screen.getByRole("group", { name: "UFs por região" });
    await user.click(within(shortcuts).getByRole("button", { name: "Bahia" }));
    expect(await mapButton("Bahia")).toHaveAttribute("aria-pressed", "true");
    await user.click(screen.getByRole("button", { name: "Limpar seleção" }));
    expect(screen.getByRole("combobox", { name: "Ou escolha uma UF" })).toHaveFocus();
  });

  it("the list picker selects a UF", async () => {
    const user = userEvent.setup();
    render(<StateExplorer />);
    await mapButton("Goiás");
    await user.selectOptions(screen.getByRole("combobox", { name: "Ou escolha uma UF" }), "GO");
    expect(screen.getByRole("region", { name: "Goiás GO" })).toHaveTextContent("Região Centro-Oeste");
    expect(await mapButton("Goiás")).toHaveAttribute("aria-pressed", "true");
  });

  it("without the official boundaries, says so and keeps the list", async () => {
    boundariesStatus = 404;
    render(<StateExplorer />);
    expect(await screen.findByText(/malha oficial das UFs \(IBGE\) ainda não foi coletada/)).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Mapa do Brasil: escolha uma UF" })).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Ou escolha uma UF" })).toBeInTheDocument();
  });
});
