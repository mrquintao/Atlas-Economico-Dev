import { chart, expect, hover, test, tooltipText } from "./fixtures";

// Expected values follow from the SYNTHETIC fixture (e2e_seed.py, state_series): bimesters and
// four-month periods of 2023-2025; SP has the nine indicators, DF all but the nominal result,
// MG only the RCL and DCL/RCL, every other UF nothing. Not official values.

const RCL = "Receita corrente líquida";
const DCL_RCL = "DCL / RCL";

/** A card in the "Últimos valores publicados" section. */
function card(page: Parameters<typeof chart>[0], name: string) {
  return page.getByRole("region", { name: "Últimos valores publicados" }).getByRole("region", { name });
}

test("lists the 27 UFs and opens a state page from the navigation", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Principal" });
  await nav.getByRole("link", { name: "Estados" }).click();
  await expect(page).toHaveURL(/\/estados$/);
  await expect(page.getByRole("heading", { level: 1, name: "Estados" })).toBeVisible();
  const links = page.getByRole("main").getByRole("link", { name: /\([A-Z]{2}\)$/ });
  await expect(links).toHaveCount(27);

  await page.getByRole("link", { name: "São Paulo (SP)" }).click();
  await expect(page).toHaveURL(/\/estados\/SP$/);
  await expect(page.getByRole("heading", { level: 1, name: "São Paulo (SP)" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Estados" })).toHaveAttribute("aria-current", "location");
});

test("SP: latest values with period, window, same-period comparison and source", async ({ page }) => {
  await page.goto("/estados/SP");
  const rcl = card(page, RCL);
  await expect(rcl).toContainText("R$ 268,00 bi");
  await expect(rcl).toContainText("Referência: 6º bim./2025 (nov–dez) · R$ correntes");
  await expect(rcl).toContainText("Últimos 12 meses até o fim do período.");
  await expect(rcl).toContainText("+R$ 24,00 bi em relação ao 6º bim./2024 (R$ 244,00 bi)");
  await expect(rcl).toContainText("sem correção pela inflação");
  await expect(rcl.getByRole("link", { name: /^Secretaria do Tesouro Nacional — SICONFI, RREO-Anexo 03/ })).toBeVisible();

  const ratio = card(page, DCL_RCL);
  await expect(ratio).toContainText("114,00% da RCL ajustada");
  await expect(ratio).toContainText("Referência: 3º quadr./2025 (set–dez)");
  await expect(ratio).toContainText("+1,50 p.p. em relação ao 3º quadr./2024");

  // The nine indicators have data: no absence section, no comparability note.
  await expect(page.getByRole("region", { name: "Últimos valores publicados" }).getByRole("region")).toHaveCount(9);
  await expect(page.getByRole("region", { name: /Indicadores sem dados/ })).toHaveCount(0);
  await expect(page.getByRole("complementary")).toHaveCount(0);
});

test("SP: charts in their own periods, synchronised across bimesters and four-month periods", async ({
  page,
}) => {
  await page.goto("/estados/SP");
  const rcl = chart(page, RCL);
  const ratio = chart(page, DCL_RCL);
  await expect(rcl).toHaveAccessibleName(/^Receita corrente líquida de 1º bim\.\/2023 a 6º bim\.\/2025/);
  await expect(ratio).toHaveAccessibleName(/^DCL \/ RCL de 1º quadr\.\/2023 a 3º quadr\.\/2025/);
  // Year-to-date flow: no change/min/max statistics.
  await expect(chart(page, "Resultado primário")).toHaveAccessibleName(
    "Resultado primário de 1º bim./2023 a 6º bim./2025: 18 valores publicados; o último é R$ 18,00 bi.",
  );

  // The last four-month period (set–dez/2025) highlights its last bimester (nov–dez), never
  // the nearest bimester point.
  await hover(page, ratio, 0.995);
  expect(await tooltipText(ratio)).toBe("114,00% da RCL ajustada Referência: 3º quadr./2025 (set–dez)");
  expect(await tooltipText(rcl)).toBe("R$ 268,00 bi Referência: 6º bim./2025 (nov–dez)");
});

test("SP: the first bimester of a year-to-date flow shows its value on hover", async ({ page }) => {
  await page.goto("/estados/SP");
  const primary = chart(page, "Resultado primário");
  await expect(primary).toBeVisible();
  // Default domain: 01/01/2023 to 31/12/2025 (end of the last bimester); 01/01/2025 sits at
  // 731 of 1095 days. January restarts the accumulation (a line break shares its date).
  await hover(page, primary, 731 / 1095);
  expect(await tooltipText(primary)).toBe("R$ 3,00 bi Referência: 1º bim./2025 (jan–fev)");
});

test("SP: the latest end date still includes the latest periods", async ({ page }) => {
  await page.goto("/estados/SP");
  await expect(chart(page, RCL)).toBeVisible();
  await page.getByLabel("Data final").fill("2025-12-31");
  await expect(chart(page, RCL)).toHaveAccessibleName(/a 6º bim\.\/2025/);
  await expect(chart(page, DCL_RCL)).toHaveAccessibleName(/a 3º quadr\.\/2025/);
  await expect(page.getByLabel("Data final")).toHaveAttribute("max", "2025-12-31");
});

test("SP: a custom period reloads every chart", async ({ page }) => {
  await page.goto("/estados/SP");
  await expect(chart(page, RCL)).toBeVisible();
  await page.getByLabel("Data inicial").fill("2025-01-01");
  await expect(chart(page, RCL)).toHaveAccessibleName(/de 1º bim\.\/2025 a 6º bim\.\/2025/);
  await expect(chart(page, DCL_RCL)).toHaveAccessibleName(/de 1º quadr\.\/2025 a 3º quadr\.\/2025/);
});

test("DF: shows the comparability note and the missing indicator", async ({ page }) => {
  await page.goto("/estados/DF");
  await expect(page.getByRole("heading", { level: 1, name: "Distrito Federal (DF)" })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Ressalva de comparabilidade" })).toContainText(
    "não são diretamente comparáveis aos dos estados",
  );
  await expect(card(page, RCL)).toContainText("R$ 53,60 bi");
  const missing = page.getByRole("region", { name: "Indicadores sem dados nesta UF" });
  await expect(missing.getByRole("listitem")).toHaveText(["Resultado nominal"]);
  await expect(chart(page, "Resultado nominal")).toHaveCount(0);
});

test("MG: only indicators with data get cards and charts; absences are explicit", async ({ page }) => {
  await page.goto("/estados/MG");
  await expect(card(page, RCL)).toContainText("R$ 134,00 bi");
  await expect(page.getByRole("region", { name: "Últimos valores publicados" }).getByRole("region")).toHaveCount(2);
  const missing = page.getByRole("region", { name: "Indicadores sem dados nesta UF" });
  await expect(missing.getByRole("listitem")).toHaveCount(7);
  await expect(missing).toContainText("não são estimados nem exibidos como zero");
  await expect(chart(page, RCL)).toBeVisible();
  await expect(chart(page, DCL_RCL)).toBeVisible();
  await expect(chart(page, "Dívida consolidada")).toHaveCount(0);
});

test("a UF without fiscal data says so instead of showing zeros", async ({ page }) => {
  await page.goto("/estados/AC");
  await expect(page.getByText("Ainda não há dados fiscais armazenados para esta UF.", { exact: false })).toBeVisible();
  await expect(page.getByRole("group", { name: "Período predefinido" })).toHaveCount(0);
  await expect(page.getByRole("img")).toHaveCount(0);
});

test("a lowercase UF redirects to the canonical page", async ({ page }) => {
  const response = await page.goto("/estados/mg");
  expect(response?.status()).toBe(200);
  await expect(page).toHaveURL(/\/estados\/MG$/);
  await expect(page.getByRole("heading", { level: 1, name: "Minas Gerais (MG)" })).toBeVisible();
});

for (const path of ["/estados/XX", "/estados/BR", "/estados/31"]) {
  test(`an invalid UF (${path}) gets a friendly 404`, async ({ page, consoleErrors }) => {
    const response = await page.goto(path);
    expect(response?.status()).toBe(404);
    await expect(page).toHaveTitle("Página não encontrada — Atlas Econômico Brasileiro");
    await expect(page.getByRole("heading", { level: 1, name: "Página não encontrada" })).toBeVisible();
    await page.getByRole("link", { name: "Ver a lista de estados" }).click();
    await expect(page).toHaveURL(/\/estados$/);
    // The browser reports the 404 document itself; nothing else may fail.
    consoleErrors.splice(0, consoleErrors.length, ...consoleErrors.filter((e) => !/status of 404/.test(e)));
  });
}

// Map (S6): the fixture's boundaries are SYNTHETIC squares, one per UF. No period reaches the
// 14-UF coverage of the default rule, so the default is the most recent period (3º quadr./2025).

function stateMap(page: Parameters<typeof chart>[0]) {
  return page.getByRole("group", { name: /^Mapa de / });
}

test("map: 27 UFs at one common period, explicit absences, legend and table", async ({ page }) => {
  await page.goto("/estados");
  const map = stateMap(page);
  await expect(map).toHaveAccessibleName("Mapa de Pessoal do Executivo / RCL por UF, 3º quadr./2025 (set–dez)");
  await expect(map.getByRole("button")).toHaveCount(27);
  await expect(map.getByRole("button", { name: "São Paulo: 44,00% da RCL ajustada, 3º quadr./2025 (set–dez)" })).toBeVisible();
  await expect(map.getByRole("button", { name: "Distrito Federal*: 44,00% da RCL ajustada, 3º quadr./2025 (set–dez)" })).toBeVisible();
  await expect(map.getByRole("button", { name: "Minas Gerais: sem dado, 3º quadr./2025 (set–dez)" })).toBeVisible();
  await expect(page.getByText("2 de 27 UFs com dado publicado neste período.")).toBeVisible();

  const legend = page.getByRole("list", { name: "Legenda do mapa" });
  await expect(legend.getByRole("listitem")).toHaveCount(2);
  await expect(legend).toContainText("44,00% da RCL ajustada (2 UFs)");
  await expect(legend).toContainText("Sem dado (25 UFs)");

  await page.getByText("Ver os valores em tabela").click();
  const table = page.getByRole("table");
  await expect(table.getByRole("row")).toHaveCount(28);
  await expect(table.getByRole("row", { name: /Minas Gerais/ })).toContainText("sem dado");
});

test("map: hover shows value, unit and period; a click shows the UF beside the map", async ({ page }) => {
  await page.goto("/estados");
  const sp = stateMap(page).getByRole("button", { name: /^São Paulo:/ });
  await sp.hover();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toContainText("São Paulo");
  await expect(tooltip).toContainText("44,00% da RCL ajustada");
  await expect(tooltip).toContainText("3º quadr./2025 (set–dez)");

  // Clicking selects the UF: same page, values in the side panel.
  await sp.click();
  await expect(sp).toHaveAttribute("aria-pressed", "true");
  await expect(page).toHaveURL(/\/estados$/);
  const panel = page.getByRole("region", { name: "São Paulo SP" });
  await expect(panel).toContainText("Região Sudeste");
  await expect(panel).toContainText("44,00% da RCL ajustada");
  const latest = panel.getByRole("region", { name: "Últimos valores publicados" });
  await expect(latest).toContainText("Receita corrente líquida");
  await expect(latest).toContainText("R$ 268,00 bi");
  await expect(latest).toContainText("6º bim./2025 (nov–dez)");

  // Another UF replaces the selection; MG has no value in this period and says so.
  await stateMap(page).getByRole("button", { name: /^Minas Gerais:/ }).click();
  const mg = page.getByRole("region", { name: "Minas Gerais MG" });
  await expect(mg).toContainText("Sem dado");
  await expect(mg.getByRole("region", { name: "Últimos valores publicados" })).toContainText("R$ 134,00 bi");
  await expect(mg).toContainText(/Sem dados nesta UF: .*Dívida consolidada/);

  await mg.getByRole("link", { name: "Abrir o painel completo da UF" }).click();
  await expect(page).toHaveURL(/\/estados\/MG$/);
  await expect(page.getByRole("heading", { level: 1, name: "Minas Gerais (MG)" })).toBeVisible();
});

test("map: keyboard focus shows the tooltip; Enter selects, Escape clears", async ({ page }) => {
  await page.goto("/estados");
  const sp = stateMap(page).getByRole("button", { name: /^São Paulo:/ });
  await sp.focus();
  await expect(page.getByRole("tooltip")).toContainText("São Paulo");
  await page.keyboard.press("Enter");
  await expect(sp).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("heading", { level: 3, name: "São Paulo SP" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(sp).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByRole("heading", { level: 3, name: "Nenhuma UF selecionada" })).toBeVisible();
});

test("map: period and indicator filters", async ({ page }) => {
  await page.goto("/estados");
  const map = stateMap(page);
  await page.getByRole("combobox", { name: "Período" }).selectOption({ label: "1º quadr./2023 (jan–abr) — 2 UFs" });
  await expect(map).toHaveAccessibleName(/1º quadr\.\/2023 \(jan–abr\)$/);
  await expect(map.getByRole("button", { name: /^São Paulo: 40,00% da RCL ajustada/ })).toBeVisible();

  // Same kind of period (four-monthly): the period is kept. DCL/RCL can be negative: diverging.
  await page.getByRole("combobox", { name: "Indicador" }).selectOption({ label: DCL_RCL });
  await expect(map).toHaveAccessibleName("Mapa de DCL / RCL por UF, 1º quadr./2023 (jan–abr)");
  await expect(map.getByRole("button", { name: /^Minas Gerais: 110,00% da RCL ajustada/ })).toBeVisible();
  await expect(page.getByText(/^Zero separa as cores/)).toBeVisible();
});

// Explorer: the geographic map at the top of /estados (same SYNTHETIC boundaries and series).

test("explorer: a geographic map; clicking a UF shows its profile beside the map", async ({ page }) => {
  await page.goto("/estados");
  const map = page.getByRole("group", { name: "Mapa do Brasil: escolha uma UF" });
  await expect(map.getByRole("button")).toHaveCount(27);
  await expect(page.getByRole("heading", { level: 3, name: "Explore o mapa" })).toBeVisible();

  const sp = map.getByRole("button", { name: "São Paulo" });
  await sp.hover();
  await expect(page.getByRole("tooltip")).toContainText("São Paulo SP");
  await sp.click();
  await expect(sp).toHaveAttribute("aria-pressed", "true");
  const profile = page.getByRole("region", { name: "São Paulo SP" });
  await expect(profile).toContainText("Região Sudeste");
  const latest = profile.getByRole("region", { name: "Últimos valores publicados" });
  await expect(latest).toContainText("R$ 268,00 bi");
  await expect(latest).toContainText("Últimos 12 meses até o fim do período.");

  // A UF without fiscal data says so instead of showing zeros.
  await map.getByRole("button", { name: "Acre" }).click();
  await expect(page.getByRole("region", { name: "Acre AC" })).toContainText(
    "Ainda não há dados fiscais armazenados para esta UF.",
  );

  await page.getByRole("region", { name: "Acre AC" }).getByRole("link", { name: "Abrir o painel completo da UF" }).click();
  await expect(page).toHaveURL(/\/estados\/AC$/);
});

test("explorer: the focus ring follows the keyboard, not mouse clicks", async ({ page }) => {
  await page.goto("/estados");
  const map = page.getByRole("group", { name: "Mapa do Brasil: escolha uma UF" });
  await map.getByRole("button", { name: "Bahia" }).click();
  await expect(map.locator("[data-focus-ring]")).toHaveCount(0);
  await page.keyboard.press("Tab");
  await expect(map.locator("[data-focus-ring]")).toHaveCount(1);
});
