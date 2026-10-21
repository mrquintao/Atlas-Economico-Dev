import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Indicator, Observation, ObservationsResponse } from "@/types/api";

import { Dashboard, storedBounds } from "./Dashboard";

// ECharts needs a real canvas; the chart itself is covered by chart-option tests.
vi.mock("./TimeSeriesChart", () => ({
  TimeSeriesChart: (props: {
    name: string;
    observations: Observation[];
    summary: string;
    step: boolean;
    domain: { min: string; max: string } | null;
  }) => (
    <div
      data-testid={`chart-${props.name}`}
      data-points={props.observations.length}
      data-step={String(props.step)}
      data-domain={props.domain ? `${props.domain.min}/${props.domain.max}` : ""}
    >
      {props.summary}
    </div>
  ),
}));

// ---- Synthetic API responses (test-only data) ----

const source = {
  acronym: "BCB",
  name: "SGS",
  organization: "Banco Central do Brasil",
  base_url: "https://api.bcb.gov.br/dados/serie",
  documentation_url: null,
};

const selic: Indicator = {
  code: "SELIC_TARGET",
  name: "Taxa de juros - Meta Selic definida pelo Copom",
  short_name: "Meta Selic",
  description: "Meta para a taxa Selic.",
  unit: "% a.a.",
  change_unit: "p.p.",
  frequency: "daily",
  geographic_level: "country",
  methodology: "Série SGS 432.",
  methodology_version: "SGS 432",
  first_available_date: "1999-03-05",
  source,
  source_series_code: "432",
  source_url: "https://dadosabertos.bcb.gov.br/dataset/432",
  first_stored_date: "1999-03-05",
  last_stored_date: "2026-10-21",
  last_collected_at: "2026-10-21T00:12:42Z",
};

const dbgg: Indicator = {
  ...selic,
  code: "DBGG_GDP",
  name: "Dívida bruta do governo geral (% PIB)",
  short_name: "Dívida bruta (DBGG)",
  description: "Dívida bruta do governo geral em proporção do PIB.",
  unit: "% do PIB",
  frequency: "monthly",
  methodology: "Série SGS 13762.",
  first_available_date: "2006-12-01",
  source_series_code: "13762",
  source_url: "https://dadosabertos.bcb.gov.br/dataset/13762",
  first_stored_date: "2006-12-01",
  last_stored_date: "2026-08-01",
};

function obs(date: string, value: number, periodStart = date): Observation {
  return { date, value, period_start: periodStart, period_end: date, partial: false };
}

function response(
  indicator: Indicator,
  observations: Observation[],
  frequency: "daily" | "monthly",
  aggregated = false,
): ObservationsResponse {
  const first = observations[0];
  const last = observations.at(-1);
  return {
    indicator,
    geography: { ibge_code: "1", acronym: "BR", name: "Brasil", geographic_level: "country" },
    unit: indicator.unit,
    original_frequency: indicator.frequency,
    frequency,
    aggregation: {
      method: aggregated ? "last_value_of_period" : "none",
      description: aggregated ? "Último valor do mês." : "Valores na frequência original.",
    },
    start_date: first?.date ?? null,
    end_date: last?.date ?? null,
    count: observations.length,
    stats:
      first && last
        ? {
            first: { date: first.date, value: first.value },
            last: { date: last.date, value: last.value },
            change: last.value - first.value,
            change_unit: "p.p.",
            min: { date: last.date, value: Math.min(first.value, last.value) },
            max: { date: first.date, value: Math.max(first.value, last.value) },
          }
        : null,
    observations,
  };
}

const selicMonthly = response(
  selic,
  [obs("2025-10-31", 15, "2025-10-01"), obs("2026-10-21", 13.75, "2026-10-01")],
  "monthly",
  true,
);
const selicDaily = response(selic, [obs("2008-01-01", 11.25), obs("2026-10-21", 13.75)], "daily");
const dbggSeries = response(
  dbgg,
  [obs("2025-08-01", 77.31, "2025-08-01"), obs("2026-08-01", 82.87, "2026-08-01")],
  "monthly",
);

/** A card in the "Indicadores em destaque" section (chart panels may share the name). */
async function findHighlight(name: string): Promise<HTMLElement> {
  const highlights = screen.getByRole("region", { name: "Indicadores em destaque" });
  // The card keeps its name while loading: wait for the loaded (not busy) card.
  await waitFor(() =>
    expect(within(highlights).getByRole("region", { name })).not.toHaveAttribute("aria-busy", "true"),
  );
  return within(highlights).getByRole("region", { name });
}

let fetchMock: ReturnType<typeof vi.fn>;
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

/** Observation requests for one indicator, excluding the full-history "latest value" request. */
function seriesRequests(code: string): URL[] {
  return fetchMock.mock.calls
    .map(([url]) => new URL(String(url)))
    .filter((u) => u.pathname.includes(`/${code}/observations`))
    .filter((u) => u.searchParams.has("start_date") || u.searchParams.get("frequency") !== "monthly");
}

/** Routes the synthetic API: catalog, Selic (card = full monthly; chart = daily) and DBGG. */
async function defaultFetch(url: string): Promise<Response> {
  const { pathname, searchParams } = new URL(url);
  if (pathname.endsWith("/api/v1/indicators")) return json([dbgg, selic]);
  const start = searchParams.get("start_date");
  if (start === "2010-01-01") {
    return json(response(pathname.includes("DBGG") ? dbgg : selic, [], "daily"));
  }
  if (start === "2001-01-01") {
    return json({ error: { code: "boom", message: "Falha simulada." } }, 500);
  }
  if (pathname.includes("DBGG_GDP")) return json(dbggSeries);
  const latestRequest = searchParams.get("frequency") === "monthly" && !start;
  return json(latestRequest ? selicMonthly : selicDaily);
}

beforeEach(() => {
  fetchMock = vi.fn(defaultFetch);
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("Dashboard", () => {
  it("shows the latest Selic value with unit, date, 12-month change and source", async () => {
    render(<Dashboard />);
    const card = await findHighlight("Meta Selic");
    expect(within(card).getByText("13,75% a.a.")).toBeInTheDocument();
    expect(within(card).getByText("Vigente em 21/10/2026")).toBeInTheDocument();
    expect(within(card).getByText("-1,25 p.p.")).toBeInTheDocument();
    expect(within(card).getByText(/vs\. 31\/10\/2025/)).toBeInTheDocument();
    expect(
      within(card).getByRole("link", { name: /Banco Central do Brasil — SGS 432/ }),
    ).toHaveAttribute("href", selic.source_url);
  });

  it("shows the latest debt ratio by reference month, in p.p. of GDP", async () => {
    render(<Dashboard />);
    const card = await findHighlight("Dívida bruta (DBGG)");
    expect(within(card).getByText("82,87% do PIB")).toBeInTheDocument();
    expect(within(card).getByText("Posição de ago/2026")).toBeInTheDocument();
    expect(within(card).getByText("+5,56 p.p.")).toBeInTheDocument();
    expect(within(card).getByText(/vs\. ago\/2025/)).toBeInTheDocument();
  });

  it("renders one synchronised chart per indicator for the default period", async () => {
    render(<Dashboard />);
    const selicChart = await screen.findByTestId("chart-Meta Selic");
    const dbggChart = await screen.findByTestId("chart-Dívida bruta (DBGG)");
    expect(selicChart).toHaveAttribute("data-step", "true");
    expect(dbggChart).toHaveAttribute("data-step", "false");
    // Same x-axis domain on both: selected start .. latest stored date of any indicator.
    await waitFor(() => expect(selicChart).toHaveAttribute("data-domain", "2008-01-01/2026-10-21"));
    expect(dbggChart).toHaveAttribute("data-domain", "2008-01-01/2026-10-21");
    expect(seriesRequests("SELIC_TARGET")[0].searchParams.get("start_date")).toBe("2008-01-01");
    expect(seriesRequests("DBGG_GDP")[0].searchParams.get("start_date")).toBe("2008-01-01");
    expect(seriesRequests("DBGG_GDP")[0].searchParams.get("frequency")).toBe("original");
  });

  it("applies the same preset to every chart", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart-Dívida bruta (DBGG)");
    await waitFor(() =>
      expect(screen.getByTestId("chart-Meta Selic").getAttribute("data-domain")).not.toBe(""),
    );
    await userEvent.click(screen.getByRole("button", { name: "5 anos" }));
    await waitFor(() => {
      expect(seriesRequests("SELIC_TARGET").at(-1)?.searchParams.get("start_date")).toBe("2021-10-01");
      expect(seriesRequests("DBGG_GDP").at(-1)?.searchParams.get("start_date")).toBe("2021-10-01");
    });
    expect(screen.getByRole("button", { name: "5 anos" })).toHaveAttribute("aria-pressed", "true");
  });

  it("switches only the Selic chart to monthly frequency", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart-Meta Selic");
    const dbggCalls = seriesRequests("DBGG_GDP").length;
    await userEvent.click(screen.getByRole("button", { name: "Mensal" }));
    await waitFor(() =>
      expect(seriesRequests("SELIC_TARGET").at(-1)?.searchParams.get("frequency")).toBe("monthly"),
    );
    expect(seriesRequests("DBGG_GDP").length).toBe(dbggCalls);
    // Only daily series offer the toggle.
    expect(screen.getAllByRole("group", { name: /^Frequência/ })).toHaveLength(1);
  });

  it("does not request an inverted custom range and explains why", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart-Meta Selic");
    const before = fetchMock.mock.calls.length;
    fireEvent.change(screen.getByLabelText("Data final"), { target: { value: "2005-01-01" } });
    expect(await screen.findByText(/data inicial deve ser anterior/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.length).toBe(before);
  });

  it("shows explicit empty states instead of zeros", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart-Meta Selic");
    fireEvent.change(screen.getByLabelText("Data inicial"), { target: { value: "2010-01-01" } });
    expect(await screen.findAllByText(/Não há observações oficiais/)).toHaveLength(2);
    expect(screen.queryByTestId("chart-Meta Selic")).not.toBeInTheDocument();
  });

  it("shows the API error with retry and keeps the last loaded data", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart-Meta Selic");
    fireEvent.change(screen.getByLabelText("Data inicial"), { target: { value: "2001-01-01" } });
    expect(await screen.findAllByText(/Falha simulada/)).toHaveLength(2);
    expect(screen.getByTestId("chart-Meta Selic")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Tentar novamente" })).toHaveLength(2);
  });

  it("shows an error state with retry when the first load fails", async () => {
    fetchMock.mockImplementation(async () => {
      throw new TypeError("Failed to fetch");
    });
    render(<Dashboard />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((a) => /backend está em execução/.test(a.textContent ?? ""))).toBe(true);
    expect(screen.getAllByRole("button", { name: "Tentar novamente" }).length).toBeGreaterThan(0);
  });
});

describe("storedBounds", () => {
  it("spans the earliest first and latest last stored dates of dashboard indicators", () => {
    expect(storedBounds([selic, dbgg])).toEqual({ first: "1999-03-05", last: "2026-10-21" });
  });

  it("ignores indicators that are not on the dashboard and missing dates", () => {
    const other = { ...selic, code: "OTHER", first_stored_date: "1900-01-01" };
    const empty = { ...dbgg, first_stored_date: null, last_stored_date: null };
    expect(storedBounds([other, empty])).toEqual({ first: null, last: null });
  });
});

describe("Dashboard loading and error states", () => {
  it("labels cards while loading and shows a status message", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
        fetchMock.mockImplementation(async (url: string) => {
      await gate;
      return defaultFetch(url);
    });
    render(<Dashboard />);
    const highlights = screen.getByRole("region", { name: "Indicadores em destaque" });
    const card = within(highlights).getByRole("region", { name: "Meta Selic" });
    expect(card).toHaveAttribute("aria-busy", "true");
    expect(within(card).getByRole("status")).toHaveTextContent("Carregando dados oficiais");
    release();
    await waitFor(() => expect(within(highlights).getByText("13,75% a.a.")).toBeInTheDocument());
  });

  it("shows 'Atualizando…' while reloading over previous data", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart-Meta Selic");
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
        fetchMock.mockImplementation(async (url: string) => {
      await gate;
      return defaultFetch(url);
    });
    await userEvent.click(screen.getByRole("button", { name: "10 anos" }));
    expect(await screen.findAllByText("Atualizando…")).toHaveLength(2);
    expect(screen.getByTestId("chart-Meta Selic")).toBeInTheDocument(); // stale data stays
    release();
    await waitFor(() => expect(screen.queryByText("Atualizando…")).not.toBeInTheDocument());
  });

  it("offers retry on a failed card and recovers", async () => {
    let failCards = true;
        fetchMock.mockImplementation(async (url: string) => {
      const u = new URL(url);
      const cardRequest = u.searchParams.get("frequency") === "monthly" && !u.searchParams.has("start_date");
      if (failCards && cardRequest && u.pathname.includes("SELIC")) {
        return json({ error: { code: "boom", message: "Cartão indisponível." } }, 503);
      }
      return defaultFetch(url);
    });
    render(<Dashboard />);
    const highlights = screen.getByRole("region", { name: "Indicadores em destaque" });
    const card = within(highlights).getByRole("region", { name: "Meta Selic" });
    expect(await within(card).findByText("Cartão indisponível.")).toBeInTheDocument();
    failCards = false;
    await userEvent.click(within(card).getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() => expect(within(highlights).getByText("13,75% a.a.")).toBeInTheDocument());
  });

  it("reports a catalog failure with retry instead of failing silently", async () => {
    let failCatalog = true;
        fetchMock.mockImplementation(async (url: string) => {
      if (failCatalog && new URL(url).pathname.endsWith("/api/v1/indicators")) {
        return json({ error: { code: "boom", message: "Catálogo fora do ar." } }, 503);
      }
      return defaultFetch(url);
    });
    render(<Dashboard />);
    const period = await screen.findByText(/Não foi possível carregar o catálogo de indicadores/);
    expect(period).toHaveTextContent("Catálogo fora do ar.");
    failCatalog = false;
    const alert = period.closest("[role=alert]") as HTMLElement;
    await userEvent.click(within(alert).getByRole("button", { name: "Tentar novamente" }));
    await waitFor(() =>
      expect(screen.queryByText(/Não foi possível carregar o catálogo/)).not.toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByTestId("chart-Meta Selic")).toHaveAttribute("data-domain", "2008-01-01/2026-10-21"),
    );
  });
});
