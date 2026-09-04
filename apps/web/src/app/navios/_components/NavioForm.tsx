// =============================================================================
// SINDESTIVA-PE · Formulário de cadastro de navio (issue #15)
// Fluxo do Salvar:
//   1. valida com Zod → se falhar, NENHUM request sai e o erro aparece
//      embaixo do campo
//   2. POST /api/v1/navios
//   3. sucesso → toast (role="status") e redirect pra /navios
//   4. erro    → alerta (role="alert") com texto amigável; o formulário
//      permanece preenchido pro Fiscal corrigir
// =============================================================================

"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent, type ReactNode } from "react";

import { criarNavio, mensagemErroNavio } from "@/lib/navios";
import {
  NAVIO_FORM_VAZIO,
  ROTULO_TIPO_OPERACAO,
  TIPOS_OPERACAO,
  validarNavioForm,
  type NavioFormValues,
} from "@/lib/schemas/navio";

/** Espera antes do redirect, pra o toast de sucesso ser lido. */
const MS_ATE_REDIRECT = 1200;

type Erros = Partial<Record<keyof NavioFormValues, string>>;

const INPUT_CLS =
  "w-full rounded border border-[#1e3a5f] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e6edf3] outline-none focus:border-[#d4a574]";

export function NavioForm(): ReactNode {
  const router = useRouter();
  const [values, setValues] = useState<NavioFormValues>(NAVIO_FORM_VAZIO);
  const [erros, setErros] = useState<Erros>({});
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  function set(campo: keyof NavioFormValues, valor: string) {
    setValues((v) => ({ ...v, [campo]: valor }));
    // Limpa o erro do campo assim que o usuário corrige.
    setErros((e) => (e[campo] ? { ...e, [campo]: undefined } : e));
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setErroGeral(null);

    const parsed = validarNavioForm(values);
    if (!parsed.ok) {
      // Barreira client-side: nada é enviado à API.
      setErros(parsed.erros);
      return;
    }
    setErros({});
    setSalvando(true);
    try {
      const navio = await criarNavio(parsed.data);
      setSucesso(`Navio "${navio.nome}" cadastrado com sucesso.`);
      setTimeout(() => {
        router.push("/navios");
        router.refresh();
      }, MS_ATE_REDIRECT);
    } catch (err) {
      // Nunca vaza status cru nem stacktrace — ver `mensagemErroNavio`.
      setErroGeral(mensagemErroNavio(err));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="max-w-2xl space-y-4">
      {sucesso && (
        <div
          role="status"
          aria-live="polite"
          className="rounded border border-[#2e7d5b] bg-[#10251c] px-4 py-3 text-[13px] text-[#7ee2b8]"
        >
          ✅ {sucesso}
        </div>
      )}

      {erroGeral && (
        <div
          role="alert"
          className="rounded border border-[#7d2e2e] bg-[#251010] px-4 py-3 text-[13px] text-[#f2a3a3]"
        >
          ⚠️ {erroGeral}
        </div>
      )}

      <div>
        <label htmlFor="nome" className="mb-1 block text-[12px] font-bold text-[#8fa8c0]">
          Nome do navio *
        </label>
        <input
          id="nome"
          name="nome"
          value={values.nome}
          onChange={(e) => set("nome", e.target.value)}
          aria-invalid={!!erros.nome}
          aria-describedby={erros.nome ? "erro-nome" : undefined}
          className={INPUT_CLS}
          placeholder="MSC Ilona"
        />
        {erros.nome && (
          <p id="erro-nome" className="mt-1 text-[12px] text-[#f2a3a3]">
            {erros.nome}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="imo" className="mb-1 block text-[12px] font-bold text-[#8fa8c0]">
          IMO (opcional)
        </label>
        <input
          id="imo"
          name="imo"
          value={values.imo}
          onChange={(e) => set("imo", e.target.value)}
          aria-invalid={!!erros.imo}
          aria-describedby={erros.imo ? "erro-imo" : undefined}
          className={INPUT_CLS}
          placeholder="IMO9319466"
        />
        {erros.imo && (
          <p id="erro-imo" className="mt-1 text-[12px] text-[#f2a3a3]">
            {erros.imo}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="bandeira" className="mb-1 block text-[12px] font-bold text-[#8fa8c0]">
          Bandeira (opcional)
        </label>
        <input
          id="bandeira"
          name="bandeira"
          value={values.bandeira}
          onChange={(e) => set("bandeira", e.target.value)}
          aria-invalid={!!erros.bandeira}
          className={INPUT_CLS}
          placeholder="Liberia"
        />
        {erros.bandeira && <p className="mt-1 text-[12px] text-[#f2a3a3]">{erros.bandeira}</p>}
      </div>

      <div>
        <label htmlFor="tipo_operacao" className="mb-1 block text-[12px] font-bold text-[#8fa8c0]">
          Tipo de operação (opcional)
        </label>
        <select
          id="tipo_operacao"
          name="tipo_operacao"
          value={values.tipo_operacao}
          onChange={(e) => set("tipo_operacao", e.target.value)}
          className={INPUT_CLS}
        >
          <option value="">—</option>
          {TIPOS_OPERACAO.map((t) => (
            <option key={t} value={t}>
              {ROTULO_TIPO_OPERACAO[t]}
            </option>
          ))}
        </select>
        {erros.tipo_operacao && (
          <p className="mt-1 text-[12px] text-[#f2a3a3]">{erros.tipo_operacao}</p>
        )}
      </div>

      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={salvando}
          className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a] disabled:opacity-50"
        >
          {salvando ? "Salvando…" : "Salvar navio"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/navios")}
          className="rounded border border-[#1e3a5f] px-4 py-2 text-[12px] font-bold text-[#8fa8c0] hover:text-[#e6edf3]"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
