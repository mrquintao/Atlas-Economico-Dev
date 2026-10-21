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
    await expect(page.getByRole("heading", { level: 1, name: "Página não encontrada" })).toBeVisible();
    await page.getByRole("link", { name: "Ver a lista de estados" }).click();
    await expect(page).toHaveURL(/\/estados$/);
    // The browser reports the 404 document itself; nothing else may fail.
    consoleErrors.splice(0, consoleErrors.length, ...consoleErrors.filter((e) => !/status of 404/.test(e)));
  });
}
