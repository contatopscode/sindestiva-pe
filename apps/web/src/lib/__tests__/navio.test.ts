// =============================================================================
// SINDESTIVA-PE · Testes do cadastro de navios (issue #15)
// Regressão de "erro ao salvar no formulário de cadastro de navios".
//
//   - schema Zod: bloqueia submit client-side (nenhum request disparado)
//   - mensagemErroNavio: 409/422/500/timeout viram texto amigável
//     (nunca "[object Object]" nem stacktrace)
// =============================================================================

import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api";
import { criarNavio, mensagemErroNavio } from "../navios";
import { navioFormSchema } from "../schemas/navio";

// ---- Zod ------------------------------------------------------------------

describe("navioFormSchema", () => {
  it("aceita cadastro só com nome", () => {
    const r = navioFormSchema.safeParse({
      nome: "MSC Ilona",
      imo: "",
      bandeira: "",
      tipo_operacao: "",
    });
    expect(r.success).toBe(true);
    if (r.success) {
      expect(r.data.nome).toBe("MSC Ilona");
      expect(r.data.imo).toBeUndefined();
    }
  });

  it("normaliza IMO digitado sem prefixo", () => {
    const r = navioFormSchema.safeParse({ nome: "MSC Ilona", imo: "9319466" });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.imo).toBe("IMO9319466");
  });

  it("normaliza IMO com espaço e caixa baixa", () => {
    const r = navioFormSchema.safeParse({ nome: "MSC Ilona", imo: "imo 9319466" });
    expect(r.success).toBe(true);
    if (r.success) expect(r.data.imo).toBe("IMO9319466");
  });

  it("faz trim do nome", () => {
    const r = navioFormSchema.safeParse({ nome: "  MSC Ilona  " });
    expect(r.success && r.data.nome).toBe("MSC Ilona");
  });

  it.each(["", "   "])("rejeita nome vazio (%j)", (nome) => {
    const r = navioFormSchema.safeParse({ nome });
    expect(r.success).toBe(false);
    if (!r.success) expect(r.error.issues[0].path).toEqual(["nome"]);
  });

  it("rejeita nome maior que 200 caracteres", () => {
    expect(navioFormSchema.safeParse({ nome: "N".repeat(201) }).success).toBe(false);
  });

  it.each(["IMO12345", "IMO123456789", "ABCDEFG", "IMO-9319466"])(
    "rejeita IMO inválido (%s)",
    (imo) => {
      const r = navioFormSchema.safeParse({ nome: "Navio X", imo });
      expect(r.success).toBe(false);
      if (!r.success) expect(r.error.issues[0].path).toEqual(["imo"]);
    },
  );

  it("rejeita tipo de operação fora do catálogo", () => {
    expect(navioFormSchema.safeParse({ nome: "Navio X", tipo_operacao: "SUBMARINO" }).success).toBe(
      false,
    );
  });
});

// ---- Mapeamento de erros --------------------------------------------------

describe("mensagemErroNavio", () => {
  it("409 vira mensagem específica de IMO duplicado", () => {
    const msg = mensagemErroNavio(
      new ApiError(409, "Já existe navio com o IMO IMO9319466.", "NAVIO_IMO_DUPLICADO"),
    );
    expect(msg).toMatch(/IMO/i);
    expect(msg).toMatch(/já (existe|está)/i);
  });

  it("422 vira mensagem de dados inválidos", () => {
    const msg = mensagemErroNavio(new ApiError(422, "validation error", "VALIDATION_ERROR"));
    expect(msg).toMatch(/inválid/i);
  });

  it("500 vira mensagem amigável sem stacktrace", () => {
    const msg = mensagemErroNavio(
      new ApiError(500, 'Traceback (most recent call last):\n  File "app/main.py"'),
    );
    expect(msg).not.toMatch(/Traceback/);
    expect(msg).not.toMatch(/\.py/);
    expect(msg).toMatch(/tente novamente/i);
  });

  it("erro de rede (status 0) explica a queda de conexão", () => {
    expect(mensagemErroNavio(new ApiError(0, "Falha de rede: timeout"))).toMatch(/conex|rede/i);
  });

  it("403 usa a mensagem da API quando ela é amigável", () => {
    expect(mensagemErroNavio(new ApiError(403, "Apenas fiscais podem cadastrar navios."))).toBe(
      "Apenas fiscais podem cadastrar navios.",
    );
  });

  it("nunca devolve [object Object]", () => {
    for (const status of [400, 409, 422, 500, 503]) {
      expect(mensagemErroNavio(new ApiError(status, "[object Object]"))).not.toContain(
        "[object Object]",
      );
    }
  });
});

// ---- criarNavio -----------------------------------------------------------

describe("criarNavio", () => {
  function mockFetch(status: number, body: unknown) {
    return vi.fn().mockResolvedValue({
      ok: status < 400,
      status,
      statusText: String(status),
      json: async () => body,
    } as unknown as Response);
  }

  it("POSTa em /api/v1/navios e devolve o navio criado", async () => {
    const criado = { id: "uuid-1", nome: "MSC Ilona", imo: "IMO9319466" };
    const fetchMock = mockFetch(201, criado);
    vi.stubGlobal("fetch", fetchMock);

    const r = await criarNavio({ nome: "MSC Ilona", imo: "IMO9319466" });

    expect(r).toEqual(criado);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/navios");
    expect(init.method).toBe("POST");
    vi.unstubAllGlobals();
  });

  it("propaga ApiError com código quando a API responde 409", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch(409, { detail: { code: "NAVIO_IMO_DUPLICADO", message: "IMO já cadastrado." } }),
    );

    await expect(criarNavio({ nome: "MSC Ilona", imo: "IMO9319466" })).rejects.toMatchObject({
      status: 409,
      code: "NAVIO_IMO_DUPLICADO",
      detail: "IMO já cadastrado.",
    });
    vi.unstubAllGlobals();
  });

  it("não deixa detail virar [object Object] quando a API manda objeto", async () => {
    vi.stubGlobal("fetch", mockFetch(500, { detail: { code: "X", message: "boom" } }));

    await expect(criarNavio({ nome: "MSC Ilona" })).rejects.toMatchObject({ detail: "boom" });
    vi.unstubAllGlobals();
  });
});
