import {
  DBGG,
  IPCA,
  SELIC,
  chart,
  dayMonth,
  expect,
  hover,
  monthIndex,
  openDashboard,
  test,
  tooltipText,
  zoomIn,
} from "./fixtures";

// Expected values follow from the SYNTHETIC fixture ranges (e2e_seed.py): Selic 2004-01-01 to
// 2026-06-30 (daily), DBGG 2006-12 to 2026-05 and IPCA 2000-01 to 2026-05 (monthly).

test("loads the national dashboard with cards and the three charts", async ({ page }) => {
  await openDashboard(page);
  await expect(page.getByRole("heading", { level: 1, name: "Brasil em Perspectiva" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Indicadores em destaque" })).toBeVisible();
  // Default period: since 2008, until the latest observation of each indicator.
  await expect(chart(page, SELIC)).toHaveAccessibleName(/^Meta Selic de 01\/01\/2008 a 30\/06\/2026/);
  await expect(chart(page, DBGG)).toHaveAccessibleName(/de jan\/2008 a mai\/2026/);
  await expect(chart(page, IPCA)).toHaveAccessibleName(/de jan\/2008 a mai\/2026/);
  await expect(page.getByText("Não foi possível carregar os dados.")).toHaveCount(0);
});

test("applies each period preset to every chart", async ({ page }) => {
  await openDashboard(page);
  const presets = page.getByRole("group", { name: "Período predefinido" });

  // "5 anos" ends at the latest observation of any indicator (2026-06-30) and starts on the
  // 1st of the month five years earlier.
  await presets.getByRole("button", { name: "5 anos" }).click();
  await expect(chart(page, SELIC)).toHaveAccessibleName(/^Meta Selic de 01\/06\/2021 a 30\/06\/2026/);
  await expect(chart(page, DBGG)).toHaveAccessibleName(/de jun\/2021 a mai\/2026/);
  await expect(chart(page, IPCA)).toHaveAccessibleName(/de jun\/2021 a mai\/2026/);
  await expect(page.getByLabel("Data inicial")).toHaveValue("2021-06-01");

  await presets.getByRole("button", { name: "10 anos" }).click();
  await expect(chart(page, SELIC)).toHaveAccessibleName(/^Meta Selic de 01\/06\/2016 a/);
  await expect(chart(page, DBGG)).toHaveAccessibleName(/de jun\/2016 a/);
  await expect(chart(page, IPCA)).toHaveAccessibleName(/de jun\/2016 a/);

  await presets.getByRole("button", { name: "Todo o histórico" }).click();
  await expect(chart(page, SELIC)).toHaveAccessibleName(/^Meta Selic de 01\/01\/2004 a/);
  await expect(chart(page, DBGG)).toHaveAccessibleName(/de dez\/2006 a/);
  await expect(chart(page, IPCA)).toHaveAccessibleName(/de jan\/2000 a/);

  await presets.getByRole("button", { name: "Desde 2008" }).click();
  await expect(chart(page, SELIC)).toHaveAccessibleName(/^Meta Selic de 01\/01\/2008 a/);
  await expect(presets.getByRole("button", { name: "Desde 2008" })).toHaveAttribute("aria-pressed", "true");
});

test("the cursor of a daily chart shows, on monthly charts, the month that contains the day", async ({
  page,
}) => {
  await openDashboard(page);
  const selic = chart(page, SELIC);
  for (const fraction of [0.15, 0.5, 0.85]) {
    await hover(page, selic, fraction);
    const day = dayMonth(await tooltipText(selic));
    for (const name of [DBGG, IPCA]) {
      const synced = await tooltipText(chart(page, name));
      expect(synced, `${name} at ${fraction}`).toContain("Referência:");
      expect(monthIndex(synced), `${name} at ${fraction}`).toBe(day.index);
    }
  }
});

test("the cursor of a monthly chart shows, on the daily chart, the last day of that month", async ({
  page,
}) => {
  await openDashboard(page);
  const dbgg = chart(page, DBGG);
  for (const fraction of [0.3, 0.7]) {
    await hover(page, dbgg, fraction);
    const month = monthIndex(await tooltipText(dbgg));
    const day = dayMonth(await tooltipText(chart(page, SELIC)));
    expect(day.index).toBe(month);
    expect(day.day).toBe(new Date(day.year, day.month, 0).getDate());
  }
});

/** Dates under the 20% and 80% positions of a chart, as month indexes. */
async function spanOf(page: Parameters<typeof hover>[0], name: string): Promise<[number, number]> {
  const target = chart(page, name);
  const read = (text: string) => (/\d{2}\/\d{2}\/\d{4}/.test(text) ? dayMonth(text).index : monthIndex(text));
  await hover(page, target, 0.2);
  const left = read(await tooltipText(target));
  await hover(page, target, 0.8);
  const right = read(await tooltipText(target));
  await page.mouse.move(0, 0);
  return [left, right];
}

test("zooming one chart zooms every chart to the same dates", async ({ page }) => {
  await openDashboard(page);
  const [before0, before1] = await spanOf(page, SELIC);
  await zoomIn(page, chart(page, SELIC), 0.5);

  const [selic0, selic1] = await spanOf(page, SELIC);
  expect(selic1 - selic0, "zoom narrows the visible span").toBeLessThan((before1 - before0) / 2);

  // The same horizontal position shows the same date on the other charts (a monthly point may
  // snap to the neighbouring month).
  for (const name of [DBGG, IPCA]) {
    const [left, right] = await spanOf(page, name);
    expect(Math.abs(left - selic0), `${name} left`).toBeLessThanOrEqual(1);
    expect(Math.abs(right - selic1), `${name} right`).toBeLessThanOrEqual(1);
  }
});

test("switching the Selic chart between daily and monthly keeps the zoom", async ({ page }) => {
  await openDashboard(page);
  const [before0, before1] = await spanOf(page, SELIC);
  await zoomIn(page, chart(page, SELIC), 0.5);
  const [daily0, daily1] = await spanOf(page, SELIC);

  await page.getByRole("group", { name: "Frequência — Meta Selic" }).getByRole("button", { name: "Mensal" }).click();
  // The monthly view describes its period by month.
  await expect(chart(page, SELIC)).toHaveAccessibleName(/^Meta Selic de jan\/2008 a jun\/2026/);
  const [monthly0, monthly1] = await spanOf(page, SELIC);
  expect(Math.abs(monthly0 - daily0)).toBeLessThanOrEqual(1);
  expect(Math.abs(monthly1 - daily1)).toBeLessThanOrEqual(1);
  expect(monthly1 - monthly0).toBeLessThan((before1 - before0) / 2);
  await expect(tooltipOf(page)).resolves.toMatch(/vigente em \d{2}\/\d{2}\/\d{4}/);
});

async function tooltipOf(page: Parameters<typeof hover>[0]): Promise<string> {
  const selic = chart(page, SELIC);
  await hover(page, selic, 0.5);
  return tooltipText(selic);
}

test("shows the empty state for charts without observations in the chosen period", async ({ page }) => {
  await openDashboard(page);
  await page.getByLabel("Data inicial").fill("2001-01-01");
  await page.getByLabel("Data final").fill("2001-12-31");

  // Selic starts in 2004 and DBGG in 2006 in the fixture; IPCA has the whole year.
  await expect(
    page.getByText("Não há observações oficiais cujo período de referência termine no intervalo selecionado."),
  ).toHaveCount(2);
  await expect(chart(page, IPCA)).toHaveAccessibleName(/de jan\/2001 a dez\/2001/);
  await expect(page.getByRole("group", { name: "Período predefinido" }).getByRole("button", { pressed: true })).toHaveCount(0);
});

test("rejects a start date after the end date without reloading the charts", async ({ page }) => {
  await openDashboard(page);
  await page.getByLabel("Data final").fill("2010-12-31");
  await expect(chart(page, SELIC)).toHaveAccessibleName(/^Meta Selic de 01\/01\/2008 a 31\/12\/2010/);
  await page.getByLabel("Data inicial").fill("2012-01-01");
  await expect(
    page.getByRole("alert").filter({ hasText: "A data inicial deve ser anterior ou igual à data final." }),
  ).toBeVisible();
  // The last valid period stays on screen.
  await expect(chart(page, SELIC)).toHaveAccessibleName(/^Meta Selic de 01\/01\/2008 a 31\/12\/2010/);
});
