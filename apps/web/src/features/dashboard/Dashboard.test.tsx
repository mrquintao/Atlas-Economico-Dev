import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Observation, ObservationsResponse } from "@/types/api";

import { Dashboard } from "./Dashboard";

// ECharts needs a real canvas; the chart itself is covered by chart-option tests.
vi.mock("./TimeSeriesChart", () => ({
  TimeSeriesChart: ({ observations, summary }: { observations: Observation[]; summary: string }) => (
    <div data-testid="chart" data-points={observations.length}>
      {summary}
    </div>
  ),
}));

// Synthetic API responses (test-only data).
const indicator = {
  code: "SELIC_TARGET",
  name: "Taxa de juros - Meta Selic definida pelo Copom",
  short_name: "Meta Selic",
  description: "Meta para a taxa Selic.",
  unit: "% a.a.",
  change_unit: "p.p.",
  frequency: "daily" as const,
  geographic_level: "country",
  methodology: "Série SGS 432.",
  methodology_version: "SGS 432",
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
  last_stored_date: "2026-10-21",
  last_collected_at: "2026-10-21T00:12:42Z",
};

function obs(date: string, value: number, periodStart = date): Observation {
  return { date, value, period_start: periodStart, period_end: date, partial: false };
}

function response(observations: Observation[], frequency: "daily" | "monthly"): ObservationsResponse {
  const first = observations[0];
  const last = observations.at(-1);
  return {
    indicator,
    geography: { ibge_code: "1", acronym: "BR", name: "Brasil", geographic_level: "country" },
    unit: "% a.a.",
    original_frequency: "daily",
    frequency,
    aggregation: {
      method: frequency === "monthly" ? "last_value_of_period" : "none",
      description: frequency === "monthly" ? "Último valor do mês." : "Valores na frequência original.",
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

const monthly = response(
  [obs("2025-10-31", 15, "2025-10-01"), obs("2026-10-21", 13.75, "2026-10-01")],
  "monthly",
);
const daily = response([obs("2008-01-01", 11.25), obs("2026-10-21", 13.75)], "daily");

let fetchMock: ReturnType<typeof vi.fn>;
const requests = () => fetchMock.mock.calls.map(([url]) => new URL(String(url)));
const seriesRequests = () => requests().filter((u) => u.searchParams.get("frequency") !== "monthly" || u.searchParams.has("start_date"));

beforeEach(() => {
  fetchMock = vi.fn(async (url: string) => {
    const params = new URL(url).searchParams;
    if (params.get("start_date") === "2010-01-01") {
      return new Response(JSON.stringify(response([], "daily")));
    }
    if (params.get("start_date") === "2001-01-01") {
      return new Response(JSON.stringify({ error: { code: "boom", message: "Falha simulada." } }), { status: 500 });
    }
    return new Response(JSON.stringify(params.get("frequency") === "monthly" && !params.has("start_date") ? monthly : daily));
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe("Dashboard", () => {
  it("shows the latest value with unit, date, 12-month change and source", async () => {
    render(<Dashboard />);
    const card = await screen.findByRole("region", { name: "Meta Selic" });
    expect(within(card).getByText("13,75% a.a.")).toBeInTheDocument();
    expect(within(card).getByText("21/10/2026")).toBeInTheDocument();
    expect(within(card).getByText("-1,25 p.p.")).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /Banco Central do Brasil — SGS 432/ })).toHaveAttribute(
      "href",
      indicator.source_url,
    );
  });

  it("loads the default period since 2008 and shows the change in p.p.", async () => {
    render(<Dashboard />);
    expect(await screen.findByTestId("chart")).toHaveAttribute("data-points", "2");
    expect(screen.getByText("+2,50 p.p.")).toBeInTheDocument();
    const first = seriesRequests()[0];
    expect(first.searchParams.get("start_date")).toBe("2008-01-01");
    expect(first.searchParams.get("frequency")).toBe("daily");
  });

  it("applies presets anchored on the latest official date", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart");
    await userEvent.click(screen.getByRole("button", { name: "5 anos" }));
    await waitFor(() =>
      expect(seriesRequests().at(-1)?.searchParams.get("start_date")).toBe("2021-10-21"),
    );
    expect(screen.getByRole("button", { name: "5 anos" })).toHaveAttribute("aria-pressed", "true");
  });

  it("switches to monthly frequency", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart");
    await userEvent.click(screen.getByRole("button", { name: "Mensal" }));
    await waitFor(() => {
      const last = seriesRequests().at(-1);
      expect(last?.searchParams.get("frequency")).toBe("monthly");
      expect(last?.searchParams.get("start_date")).toBe("2008-01-01");
    });
  });

  it("does not request an inverted custom range and explains why", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart");
    const before = fetchMock.mock.calls.length;
    fireEvent.change(screen.getByLabelText("Data final"), { target: { value: "2005-01-01" } });
    expect(await screen.findByText(/data inicial deve ser anterior/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.length).toBe(before);
  });

  it("shows an explicit empty state instead of zeros", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart");
    fireEvent.change(screen.getByLabelText("Data inicial"), { target: { value: "2010-01-01" } });
    expect(await screen.findByText(/Não há observações oficiais/)).toBeInTheDocument();
    expect(screen.queryByTestId("chart")).not.toBeInTheDocument();
  });

  it("shows the API error and keeps the last loaded data", async () => {
    render(<Dashboard />);
    await screen.findByTestId("chart");
    fireEvent.change(screen.getByLabelText("Data inicial"), { target: { value: "2001-01-01" } });
    expect(await screen.findByText(/Falha simulada/)).toBeInTheDocument();
    expect(screen.getByTestId("chart")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("shows an error state with retry when the first load fails", async () => {
    fetchMock.mockImplementation(async () => {
      throw new TypeError("Failed to fetch");
    });
    render(<Dashboard />);
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((a) => /backend está em execução/.test(a.textContent ?? ""))).toBe(true);
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});
