// =============================================================================
// SINDESTIVA-PE · E2E · Cadastro de navios (issue #15)
// Regressão de "erro ao salvar no formulário de cadastro de navios".
//
// Critérios cobertos:
//   1. save feliz → toast de sucesso + redirect pra /navios
//   2. IMO duplicado (409) → mensagem específica, sem stacktrace
//   3. 500 → mensagem amigável e formulário preservado
//   4. campos obrigatórios vazios → submit bloqueado, ZERO requests
// =============================================================================

import { expect, test, type Page, type Request } from "@playwright/test";

const API_NAVIOS = "**/api/v1/navios";

/** Coleta todos os requests que saem pro endpoint de navios. */
function espionarRequests(page: Page): Request[] {
  const reqs: Request[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/v1/navios")) reqs.push(r);
  });
  return reqs;
}

async function mockListaVazia(page: Page) {
  await page.route(`${API_NAVIOS}?*`, (route) =>
    route.fulfill({ status: 200, json: { items: [], total: 0, skip: 0, limit: 50 } }),
  );
}

test.beforeEach(async ({ page }) => {
  // Evita o redirect pra /login do apiFetch em 401.
  await page.addInitScript(() => {
    window.localStorage.setItem("sindestiva.jwt", "e2e-token");
  });
  await mockListaVazia(page);
});

test("save feliz exibe toast de sucesso e redireciona pra /navios", async ({ page }) => {
  await page.route(API_NAVIOS, async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 201,
      json: {
        id: "uuid-1",
        nome: "MSC Ilona",
        imo: "IMO9319466",
        created_at: "2026-09-04T12:00:00Z",
      },
    });
  });

  await page.goto("/navios/novo");
  await page.getByLabel(/nome do navio/i).fill("MSC Ilona");
  await page.getByLabel(/imo/i).fill("9319466");
  await page.getByRole("button", { name: /salvar/i }).click();

  await expect(page.getByRole("status")).toContainText(/cadastrad/i);
  await expect(page).toHaveURL(/\/navios$/);
});

test("IMO duplicado (409) exibe mensagem específica sem stacktrace", async ({ page }) => {
  await page.route(API_NAVIOS, async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 409,
      json: {
        detail: {
          code: "NAVIO_IMO_DUPLICADO",
          message: "Já existe um navio cadastrado com o IMO IMO9319466.",
        },
      },
    });
  });

  await page.goto("/navios/novo");
  await page.getByLabel(/nome do navio/i).fill("MSC Ilona");
  await page.getByLabel(/imo/i).fill("IMO9319466");
  await page.getByRole("button", { name: /salvar/i }).click();

  const alerta = page.getByRole("alert");
  await expect(alerta).toContainText(/IMO/);
  await expect(alerta).not.toContainText(/Traceback/);
  await expect(alerta).not.toContainText(/\[object Object\]/);
  // Formulário continua na página, sem redirect.
  await expect(page).toHaveURL(/\/navios\/novo$/);
  await expect(page.getByLabel(/nome do navio/i)).toHaveValue("MSC Ilona");
});

test("erro 500 exibe mensagem amigável e mantém o formulário íntegro", async ({ page }) => {
  await page.route(API_NAVIOS, async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    return route.fulfill({
      status: 500,
      body: 'Traceback (most recent call last):\n  File "app/main.py", line 1',
      contentType: "text/plain",
    });
  });

  await page.goto("/navios/novo");
  await page.getByLabel(/nome do navio/i).fill("Cap San Lorenzo");
  await page.getByLabel(/bandeira/i).fill("Liberia");
  await page.getByRole("button", { name: /salvar/i }).click();

  const alerta = page.getByRole("alert");
  await expect(alerta).toContainText(/tente novamente/i);
  await expect(alerta).not.toContainText(/Traceback/);
  await expect(page.getByLabel(/nome do navio/i)).toHaveValue("Cap San Lorenzo");
  await expect(page.getByLabel(/bandeira/i)).toHaveValue("Liberia");
});

test("submit com campos obrigatórios vazios é bloqueado e não dispara request", async ({
  page,
}) => {
  await page.goto("/navios/novo");
  const requests = espionarRequests(page);

  await page.getByRole("button", { name: /salvar/i }).click();

  await expect(page.getByText(/nome do navio é obrigatório/i)).toBeVisible();
  expect(requests.filter((r) => r.method() === "POST")).toHaveLength(0);
  await expect(page).toHaveURL(/\/navios\/novo$/);
});

test("IMO com formato inválido é bloqueado no client sem request", async ({ page }) => {
  await page.goto("/navios/novo");
  const requests = espionarRequests(page);

  await page.getByLabel(/nome do navio/i).fill("Navio X");
  await page.getByLabel(/imo/i).fill("12345");
  await page.getByRole("button", { name: /salvar/i }).click();

  await expect(page.getByText(/IMO deve ter 7 dígitos/i)).toBeVisible();
  expect(requests.filter((r) => r.method() === "POST")).toHaveLength(0);
});
