import { defineConfig, devices } from "@playwright/test";

/**
 * Browser end-to-end tests (e2e/). They run against the production build of the web app and the
 * real API, backed by a test database filled with the SYNTHETIC fixture
 * services/api/tests/fixtures/e2e_seed.py: never against collected official data and never
 * calling the official sources. See docs/testing-e2e.md.
 *
 * Prerequisites: `npm run build`; DATABASE_URL pointing to the seeded test database.
 * PLAYWRIGHT_CHROMIUM_EXECUTABLE overrides the browser (e.g. a preinstalled Chromium).
 */
const CI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  // The charts share module-level sync state per page, and the API/DB are shared: one worker.
  workers: 1,
  forbidOnly: CI,
  // A flaky E2E is a bug to fix, not to retry (AGENT_POLICY §4).
  retries: 0,
  reporter: CI ? [["list"], ["html", { open: "never" }]] : "list",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: "http://localhost:3000",
    locale: "pt-BR",
    timezoneId: "America/Sao_Paulo",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 900 },
        launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined },
      },
    },
  ],
  webServer: [
    {
      command: "uv run uvicorn app.main:app --port 8000",
      cwd: "../../services/api",
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: !CI,
      timeout: 60_000,
    },
    {
      command: "npm run start -- --port 3000",
      url: "http://localhost:3000",
      reuseExistingServer: !CI,
      timeout: 60_000,
    },
  ],
});
