import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures";

// Expected values follow from the SYNTHETIC fixture (e2e_seed.py, state_series): SP has the
// nine state indicators, DF all but the nominal result, MG only the RCL and DCL/RCL; every other
// UF has nothing. DCL/RCL is the same ratio (114,00% in the 3º quadr./2025) in the three UFs.
// Not official values.

function ranking(page: Page) {
  return page.getByRole("region", { name: "Ranking das UFs" });
}

function rows(page: Page) {
  return ranking(page).getByRole("table").getByRole("row");
}

test("opens from /estados and ranks the UFs by the default relative metric", async ({ page }) => {
  await page.goto("/estados");
  await page.getByRole("link", { name: "Comparar UFs: ranking e evolução histórica" }).click();
  await expect(page).toHaveURL(/\/estados\/comparar$/);
  await expect(page.getByRole("heading", { level: 1, name: "Comparar UFs" })).toBeVisible();

  const panel = ranking(page);
  await expect(panel.getByRole("combobox", { name: "Indicador" })).toHaveValue("STATE_DCL_RCL");
  await expect(panel.getByRole("combobox", { name: "Período" })).toHaveValue("2025-09-01");
  // Equal values share the position; within a tie, the UFs follow their acronyms.
  await expect(rows(page)).toHaveText([
    /Posição/,
    "1ºDistrito Federal* (DF)114,00% da RCL ajustada",
    "1ºMinas Gerais (MG)114,00% da RCL ajustada",
    "1ºSão Paulo (SP)114,00% da RCL ajustada",
  ]);
  await expect(panel).toContainText("3 de 27 UFs selecionadas com dado publicado neste período.");
  await expect(panel).toContainText("Sem dado no período: AC, AL, AM");
  await expect(panel).toContainText("Ausência de dado não equivale a zero.");
  await expect(panel).toContainText("A posição não indica desempenho melhor ou pior.");
  await expect(panel).toContainText("* O Distrito Federal acumula competências");
  await expect(panel.getByRole("note").filter({ hasText: "Valor absoluto" })).toHaveCount(0);
});

test("absolute values carry the size warning; order and selection are applied", async ({ page }) => {
  const response = await page.goto("/estados/comparar");
  expect(response?.status()).toBe(200);
  const panel = ranking(page);
  await panel.getByRole("combobox", { name: "Indicador" }).selectOption("STATE_RCL");
  await expect(panel.getByRole("combobox", { name: "Período" })).toHaveValue("2025-11-01");
  await expect(panel).toContainText("Valor absoluto: a ordem reflete sobretudo o tamanho de cada UF.");
  await expect(rows(page)).toHaveText([
    /Posição/,
    "1ºSão Paulo (SP)R$ 268,00 bi",
    "2ºMinas Gerais (MG)R$ 134,00 bi",
    "3ºDistrito Federal* (DF)R$ 53,60 bi",
  ]);

  await panel.getByRole("button", { name: "Menor → maior" }).click();
  await expect(rows(page).nth(1)).toHaveText("1ºDistrito Federal* (DF)R$ 53,60 bi");
  await expect(panel).toContainText("do menor para o maior");

  await panel.getByText(/^UFs selecionadas/).click();
  await panel.getByRole("button", { name: "Nenhuma" }).click();
  await expect(panel.getByRole("alert")).toContainText("Selecione ao menos 2 UFs");
  await panel.getByRole("checkbox", { name: "SP (São Paulo)" }).check();
  await panel.getByRole("checkbox", { name: "RJ (Rio de Janeiro)" }).check();
  await expect(rows(page)).toHaveText([/Posição/, "1ºSão Paulo (SP)R$ 268,00 bi"]);
  await expect(panel).toContainText("1 de 2 UFs selecionadas");
  await expect(panel).toContainText("Sem dado no período: RJ. Não há valor armazenado para essa UF");
  await expect(panel).not.toContainText("O Distrito Federal acumula");
});

test("historical comparison: one line per UF, absences listed apart", async ({ page }) => {
  await page.goto("/estados/comparar");
  const panel = page.getByRole("region", { name: "Evolução histórica" });
  const chart = panel.getByRole("img", { name: /por UF\./ });
  await expect(chart).toHaveAccessibleName(/^DCL \/ RCL por UF\. SP: 9 valores de 1º quadr\.\/2023 a 3º quadr\.\/2025/);
  await expect(chart).toHaveAccessibleName(/MG: 9 valores .*; RJ: sem dado\.$/);
  await expect(panel).toContainText("Sem dado: Rio de Janeiro. Nenhum valor de DCL / RCL armazenado para essa UF");

  await panel.getByRole("checkbox", { name: "DF (Distrito Federal)" }).check();
  await expect(chart).toHaveAccessibleName(/DF: 9 valores/);
  await expect(panel.getByRole("checkbox", { checked: true })).toHaveCount(4);
  await expect(panel).toContainText("* O Distrito Federal acumula competências");

  await panel.getByRole("combobox", { name: "Indicador" }).selectOption("STATE_PRIMARY_RESULT");
  await expect(chart).toHaveAccessibleName(/^Resultado primário por UF\. SP: 18 valores/);
  await expect(panel).toContainText("recomeçam em janeiro");
  await expect(panel).toContainText("Sem dado: Minas Gerais, Rio de Janeiro.");
});
