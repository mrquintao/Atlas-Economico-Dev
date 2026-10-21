import { expect, test as base, type Locator, type Page } from "@playwright/test";

/**
 * Every test fails if the page logs a console error or throws an uncaught exception.
 * The data come from the SYNTHETIC fixture (services/api/tests/fixtures/e2e_seed.py).
 */
export const test = base.extend<{ consoleErrors: string[] }>({
  consoleErrors: [
    async ({ page }, use) => {
      const errors: string[] = [];
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });
      page.on("pageerror", (error) => errors.push(String(error)));
      await use(errors);
      expect(errors, "console errors").toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };

/** Short names of the dashboard indicators, as served by the catalog. */
export const SELIC = "Meta Selic";
export const DBGG = "Dívida bruta (DBGG)";
export const IPCA = "IPCA 12 meses";

/** Chart container: its accessible name is the textual summary "<short name> de <início> a <fim>…". */
export function chart(page: Page, shortName: string): Locator {
  const escaped = shortName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return page.getByRole("img", { name: new RegExp(`^${escaped} (de|:)`) });
}

/** Grid of every chart (chart-option.ts): left 44 px, right 16 px, top 32 px, bottom 72 px. */
const GRID = { left: 44, right: 16, top: 32, bottom: 72 };

/** Moves the mouse to a horizontal fraction (0–1) of a chart's plot area. */
export async function hover(page: Page, target: Locator, fraction: number): Promise<void> {
  await target.scrollIntoViewIfNeeded();
  const box = await target.boundingBox();
  if (!box) throw new Error("chart not visible");
  const width = box.width - GRID.left - GRID.right;
  const height = box.height - GRID.top - GRID.bottom;
  await page.mouse.move(box.x + GRID.left + width * fraction, box.y + GRID.top + height / 2, {
    steps: 4,
  });
}

/** A chart's ECharts tooltip (an HTML element inside the chart container, once shown). */
export function tooltip(target: Locator): Locator {
  return target.locator(":scope > div").filter({ hasText: /\d{4}/ });
}

/** Text of a chart's visible ECharts tooltip. */
export async function tooltipText(target: Locator): Promise<string> {
  await expect(tooltip(target)).toBeVisible();
  return (await tooltip(target).innerText()).replace(/\s+/g, " ").trim();
}

const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** Month index (year * 12 + month) of the first "dd/mm/aaaa" in a text. */
export function dayMonth(text: string): { index: number; day: number; month: number; year: number } {
  const match = /(\d{2})\/(\d{2})\/(\d{4})/.exec(text);
  if (!match) throw new Error(`no dd/mm/aaaa date in "${text}"`);
  const [day, month, year] = [Number(match[1]), Number(match[2]), Number(match[3])];
  return { index: year * 12 + month - 1, day, month, year };
}

/** Month index (year * 12 + month) of the first "mmm/aaaa" in a text. */
export function monthIndex(text: string): number {
  const match = /\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\/(\d{4})\b/.exec(text);
  if (!match) throw new Error(`no mmm/aaaa month in "${text}"`);
  return Number(match[2]) * 12 + MONTHS.indexOf(match[1]);
}

/** Dates (month indexes) under the 20% and 80% positions of a chart's plot area. */
export async function spanOf(page: Page, target: Locator): Promise<[number, number]> {
  const read = (text: string) =>
    /\d{2}\/\d{2}\/\d{4}/.test(text) ? dayMonth(text).index : monthIndex(text);
  await hover(page, target, 0.2);
  const left = read(await tooltipText(target));
  await hover(page, target, 0.8);
  const right = read(await tooltipText(target));
  await page.mouse.move(0, 0);
  return [left, right];
}

/**
 * Zooms a chart in with the mouse wheel, centred at a horizontal fraction of its plot area, and
 * waits until the zoom settles (ECharts throttles dataZoom updates).
 */
export async function zoomIn(page: Page, target: Locator, fraction: number): Promise<void> {
  await hover(page, target, fraction);
  for (let i = 0; i < 12; i++) {
    await page.mouse.wheel(0, -400);
  }
  await page.mouse.move(0, 0);
  let previous = "";
  await expect
    .poll(async () => {
      const current = JSON.stringify(await spanOf(page, target));
      const stable = current === previous;
      previous = current;
      return stable;
    })
    .toBe(true);
}

/** Waits until every dashboard chart has loaded the default period. */
export async function openDashboard(page: Page): Promise<void> {
  await page.goto("/");
  for (const name of [SELIC, DBGG, IPCA]) {
    await expect(chart(page, name)).toBeVisible();
  }
}
