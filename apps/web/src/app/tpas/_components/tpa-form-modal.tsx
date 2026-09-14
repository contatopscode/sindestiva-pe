"use client";

import type { AdminTpa, AdminTpaCreatePayload, AdminTpaUpdatePayload } from "@/lib/api";
import type { TpaFuncaoMeta } from "@/lib/api";
import type { ReactNode } from "react";

export interface TpaFormValues {
  cpf: string;
  nome_completo: string;
  matricula_ogmo: string;
  telefone: string;
  email: string;
  funcao_base_id: string;
  status_cadastro: AdminTpa["status_cadastro"];
}

const EMPTY: TpaFormValues = {
  cpf: "",
  nome_completo: "",
  matricula_ogmo: "",
  telefone: "",
  email: "",
  funcao_base_id: "",
  status_cadastro: "ATIVO",
};

export function emptyTpaFormValues(): TpaFormValues {
  return { ...EMPTY };
}

export function valuesFromTpa(tpa: AdminTpa): TpaFormValues {
  return {
    cpf: tpa.cpf,
    nome_completo: tpa.nome_completo,
    matricula_ogmo: tpa.matricula_ogmo,
    telefone: tpa.telefone,
    email: tpa.email ?? "",
    funcao_base_id: tpa.funcao_base_id,
    status_cadastro: tpa.status_cadastro,
  };
}

export function toCreatePayload(values: TpaFormValues): AdminTpaCreatePayload {
  const payload: AdminTpaCreatePayload = {
    cpf: values.cpf.replace(/\D/g, ""),
    nome_completo: values.nome_completo.trim(),
    matricula_ogmo: values.matricula_ogmo.trim(),
    telefone: values.telefone.trim(),
    funcao_base_id: values.funcao_base_id,
    status_cadastro: values.status_cadastro,
  };
  if (values.email.trim()) {
    payload.email = values.email.trim();
  }
  return payload;
}

export function toUpdatePayload(values: TpaFormValues): AdminTpaUpdatePayload {
  const payload: AdminTpaUpdatePayload = {
    nome_completo: values.nome_completo.trim(),
    matricula_ogmo: values.matricula_ogmo.trim(),
    telefone: values.telefone.trim(),
    funcao_base_id: values.funcao_base_id,
    status_cadastro: values.status_cadastro,
  };
  if (values.email.trim()) {
    payload.email = values.email.trim();
  }
  return payload;
}

interface TpaFormModalProps {
  open: boolean;
  mode: "create" | "edit";
  values: TpaFormValues;
  funcoes: TpaFuncaoMeta[];
  saving: boolean;
  error: string | null;
  onChange: (next: TpaFormValues) => void;
  onClose: () => void;
  onSubmit: () => void;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-[12px] text-[#94a8bd]">
      <span>{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "rounded border border-[#1e3a52] bg-[#0d2137] px-3 py-2 text-[13px] text-[#e8eef4] outline-none focus:border-[#d4a574]/60 disabled:opacity-60";

export function TpaFormModal({
  open,
  mode,
  values,
  funcoes,
  saving,
  error,
  onChange,
  onClose,
  onSubmit,
}: TpaFormModalProps): ReactNode {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-[#1e3a52] bg-[#0a1929] p-5 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tpa-form-title"
      >
        <h2 id="tpa-form-title" className="mb-4 text-lg font-semibold text-[#e8eef4]">
          {mode === "create" ? "Novo TPA" : "Editar TPA"}
        </h2>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="CPF">
            <input
              className={inputCls}
              value={values.cpf}
              disabled={mode === "edit"}
              onChange={(e) => onChange({ ...values, cpf: e.target.value })}
            />
          </Field>
          <Field label="Matrícula OGMO">
            <input
              className={inputCls}
              value={values.matricula_ogmo}
              onChange={(e) => onChange({ ...values, matricula_ogmo: e.target.value })}
            />
          </Field>
          <Field label="Nome completo">
            <input
              className={inputCls}
              value={values.nome_completo}
              onChange={(e) => onChange({ ...values, nome_completo: e.target.value })}
            />
          </Field>
          <Field label="Telefone">
            <input
              className={inputCls}
              value={values.telefone}
              onChange={(e) => onChange({ ...values, telefone: e.target.value })}
            />
          </Field>
          <Field label="E-mail (opcional)">
            <input
              className={inputCls}
              type="email"
              placeholder="vazio → tpa+cpf@sindestiva.local"
              value={values.email}
              onChange={(e) => onChange({ ...values, email: e.target.value })}
            />
          </Field>
          <Field label="Status cadastro">
            <select
              className={inputCls}
              value={values.status_cadastro}
              onChange={(e) =>
                onChange({
                  ...values,
                  status_cadastro: e.target.value as AdminTpa["status_cadastro"],
                })
              }
            >
              <option value="ATIVO">Ativo</option>
              <option value="AFASTADO">Afastado</option>
              <option value="SUSPENSO">Suspenso</option>
              <option value="DESLIGADO">Desligado</option>
            </select>
          </Field>
          <Field label="Função base">
            <select
              className={`${inputCls} sm:col-span-2`}
              value={values.funcao_base_id}
              onChange={(e) => onChange({ ...values, funcao_base_id: e.target.value })}
            >
              <option value="">Selecione…</option>
              {funcoes.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.nome_exibicao} ({f.codigo})
                </option>
              ))}
            </select>
          </Field>
        </div>

        {error && (
          <p className="mt-3 rounded border border-[#e04a4a]/40 bg-[#e04a4a]/10 px-3 py-2 text-[12px] text-[#e04a4a]">
            {error}
          </p>
        )}

        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            className="rounded border border-[#2a5070] px-4 py-2 text-[13px] text-[#94a8bd] hover:bg-[#163554]"
            onClick={onClose}
            disabled={saving}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="rounded bg-[#d4a574] px-4 py-2 text-[13px] font-semibold text-[#0a1929] hover:bg-[#e0b585] disabled:opacity-50"
            onClick={onSubmit}
            disabled={saving || !values.funcao_base_id}
          >
            {saving ? "Salvando…" : "Salvar"}
          </button>
        </div>
      </div>
    </div>
  );
}
