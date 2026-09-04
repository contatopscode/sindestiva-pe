// =============================================================================
// SINDESTIVA-PE · Playwright (E2E)
// Roda contra o Centro de Comando (apps/web) em :3010.
// A API é interceptada por `page.route` nos specs — não precisa de
// Postgres nem da FastAPI de pé pra rodar o E2E.
//
//   pnpm install && pnpm exec playwright install chromium
//   pnpm test:e2e
// =============================================================================

import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.E2E_PORT ?? 3010);
const BASE_URL = process.env.E2E_BASE_URL ?? `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    locale: "pt-BR",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: "pnpm --filter=@sindestiva/web dev",
        url: BASE_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
