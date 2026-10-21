import { SELIC, chart, expect, test } from "./fixtures";

test("navigates from the dashboard to the methodology and sources pages", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Principal" });
  await expect(nav.getByRole("link", { name: "Brasil" })).toHaveAttribute("aria-current", "page");

  await nav.getByRole("link", { name: "Metodologia" }).click();
  await expect(page).toHaveURL(/\/metodologia$/);
  await expect(page.getByRole("heading", { level: 1, name: "Metodologia" })).toBeVisible();
  for (const name of ["Meta Selic", "Dívida bruta (DBGG)", "IPCA 12 meses"]) {
    await expect(page.getByRole("region", { name })).toBeVisible();
  }
  // Stored range of the SYNTHETIC fixture.
  await expect(page.getByRole("region", { name: "Meta Selic" })).toContainText("01/01/2004 a 30/06/2026");

  await nav.getByRole("link", { name: "Fontes de dados" }).click();
  await expect(page).toHaveURL(/\/fontes$/);
  const bcb = page.getByRole("region", { name: "Banco Central do Brasil (BCB)" });
  await expect(bcb.getByRole("link", { name: "Meta Selic" })).toBeVisible();
  await bcb.getByRole("link", { name: "Meta Selic" }).click();
  await expect(page).toHaveURL(/\/metodologia#SELIC_TARGET$/);
  await expect(page.getByRole("region", { name: "Meta Selic" })).toBeInViewport();
});

test("links each chart's methodology panel to the indicator on the methodology page", async ({ page }) => {
  await page.goto("/");
  // The Selic card (charts load in any order, so do not rely on the first panel on the page).
  const card = page.locator("section", { has: chart(page, SELIC) });
  await card.getByText("Sobre o indicador e a metodologia").click();
  await card.getByRole("link", { name: "Ver este indicador na página de metodologia" }).click();
  await expect(page).toHaveURL(/\/metodologia#SELIC_TARGET$/);
  await expect(page.getByRole("region", { name: "Meta Selic" })).toBeInViewport();
});
