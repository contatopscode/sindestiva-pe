"use client";

import type { AdminUser, AdminUserCreatePayload, AdminUserUpdatePayload } from "@/lib/api";
import type { ReactNode } from "react";
import { canSubmitUserForm, userFormMissingFields } from "./user-form-validation";

export interface UserFormValues {
  email: string;
  telefone: string;
  password: string;
  role: "FISCAL" | "DIRIGENTE";
  status: AdminUser["status"];
  cpf: string;
  nome_completo: string;
  matricula_sindicato: string;
  porto_codigo: string;
  turno_codigo: string;
  cargo: string;
}

const EMPTY: UserFormValues = {
  email: "",
  telefone: "",
  password: "",
  role: "FISCAL",
  status: "ATIVO",
  cpf: "",
  nome_completo: "",
  matricula_sindicato: "",
  porto_codigo: "SUAPE",
  turno_codigo: "DIURNO",
  cargo: "Dirigente",
};

export function valuesFromUser(user: AdminUser): UserFormValues {
  return {
    email: user.email ?? "",
    telefone: user.telefone ?? "",
    password: "",
    role: user.role,
    status: user.status,
    cpf: user.cpf ?? "",
    nome_completo: user.nome_completo ?? "",
    matricula_sindicato: user.matricula_sindicato ?? "",
    porto_codigo: user.porto_codigo ?? "SUAPE",
    turno_codigo: user.turno_codigo ?? "DIURNO",
    cargo: user.cargo ?? "Dirigente",
  };
}

export function emptyFormValues(role: "FISCAL" | "DIRIGENTE" = "FISCAL"): UserFormValues {
  return { ...EMPTY, role };
}

export function toCreatePayload(values: UserFormValues): AdminUserCreatePayload {
  const base: AdminUserCreatePayload = {
    email: values.email.trim(),
    telefone: values.telefone.trim(),
    password: values.password,
    role: values.role,
    status: values.status,
    cpf: values.cpf.replace(/\D/g, ""),
    nome_completo: values.nome_completo.trim(),
    matricula_sindicato: values.matricula_sindicato.trim(),
  };
  if (values.role === "FISCAL") {
    base.porto_codigo = values.porto_codigo;
    base.turno_codigo = values.turno_codigo;
  } else {
    base.cargo = values.cargo.trim() || "Dirigente";
  }
  return base;
}

export function toUpdatePayload(values: UserFormValues): AdminUserUpdatePayload {
  const payload: AdminUserUpdatePayload = {
    email: values.email.trim(),
    telefone: values.telefone.trim(),
    role: values.role,
    status: values.status,
    cpf: values.cpf.replace(/\D/g, ""),
    nome_completo: values.nome_completo.trim(),
    matricula_sindicato: values.matricula_sindicato.trim(),
  };
  if (values.role === "FISCAL") {
    payload.porto_codigo = values.porto_codigo;
    payload.turno_codigo = values.turno_codigo;
  } else {
    payload.cargo = values.cargo.trim() || "Dirigente";
  }
  return payload;
}

interface UserFormModalProps {
  open: boolean;
  mode: "create" | "edit";
  values: UserFormValues;
  saving: boolean;
  error: string | null;
  onChange: (next: UserFormValues) => void;
  onClose: () => void;
  onSubmit: () => void;
}

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-[12px] text-[#94a8bd]">
      <span>{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "rounded border border-[#1e3a52] bg-[#0d2137] px-3 py-2 text-[13px] text-[#e8eef4] outline-none focus:border-[#d4a574]/60";

export function UserFormModal({
  open,
  mode,
  values,
  saving,
  error,
  onChange,
  onClose,
  onSubmit,
}: UserFormModalProps): ReactNode {
  if (!open) return null;

  const missing = userFormMissingFields(values, mode);
  const canSubmit = canSubmitUserForm(values, mode);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-[#1e3a52] bg-[#0a1929] p-5 shadow-xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-form-title"
      >
        <h2 id="user-form-title" className="mb-4 text-lg font-semibold text-[#e8eef4]">
          {mode === "create" ? "Novo usuário" : "Editar usuário"}
        </h2>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="E-mail">
            <input
              className={inputCls}
              type="email"
              value={values.email}
              onChange={(e) => onChange({ ...values, email: e.target.value })}
            />
          </Field>
          <Field label="Telefone">
            <input
              className={inputCls}
              value={values.telefone}
              onChange={(e) => onChange({ ...values, telefone: e.target.value })}
            />
          </Field>
          {mode === "create" && (
            <Field label="Senha inicial">
              <input
                className={inputCls}
                type="password"
                autoComplete="new-password"
                value={values.password}
                onChange={(e) => onChange({ ...values, password: e.target.value })}
              />
            </Field>
          )}
          <Field label="Perfil (role)">
            <select
              className={inputCls}
              value={values.role}
              onChange={(e) =>
                onChange({ ...values, role: e.target.value as "FISCAL" | "DIRIGENTE" })
              }
            >
              <option value="FISCAL">Fiscal</option>
              <option value="DIRIGENTE">Dirigente</option>
            </select>
          </Field>
          <Field label="Status">
            <select
              className={inputCls}
              value={values.status}
              onChange={(e) =>
                onChange({ ...values, status: e.target.value as AdminUser["status"] })
              }
            >
              <option value="ATIVO">Ativo</option>
              <option value="INATIVO">Inativo</option>
              <option value="PENDENTE_ACEITE">Pendente aceite</option>
              <option value="BLOQUEADO">Bloqueado</option>
            </select>
          </Field>
          <Field label="CPF">
            <input
              className={inputCls}
              value={values.cpf}
              onChange={(e) => onChange({ ...values, cpf: e.target.value })}
            />
          </Field>
          <Field label="Nome completo">
            <input
              className={inputCls}
              value={values.nome_completo}
              onChange={(e) => onChange({ ...values, nome_completo: e.target.value })}
            />
          </Field>
          <Field label="Matrícula sindicato">
            <input
              className={inputCls}
              value={values.matricula_sindicato}
              onChange={(e) => onChange({ ...values, matricula_sindicato: e.target.value })}
            />
          </Field>
          {values.role === "FISCAL" ? (
            <>
              <Field label="Porto">
                <select
                  className={inputCls}
                  value={values.porto_codigo}
                  onChange={(e) => onChange({ ...values, porto_codigo: e.target.value })}
                >
                  <option value="SUAPE">Suape</option>
                  <option value="RECIFE">Recife</option>
                </select>
              </Field>
              <Field label="Turno">
                <select
                  className={inputCls}
                  value={values.turno_codigo}
                  onChange={(e) => onChange({ ...values, turno_codigo: e.target.value })}
                >
                  <option value="DIURNO">Diurno</option>
                  <option value="NOTURNO">Noturno</option>
                </select>
              </Field>
            </>
          ) : (
            <Field label="Cargo">
              <input
                className={inputCls}
                value={values.cargo}
                onChange={(e) => onChange({ ...values, cargo: e.target.value })}
              />
            </Field>
          )}
        </div>

        {error && (
          <p className="mt-3 rounded border border-[#e04a4a]/40 bg-[#e04a4a]/10 px-3 py-2 text-[12px] text-[#e04a4a]">
            {error}
          </p>
        )}

        {!canSubmit && missing.length > 0 && (
          <p className="mt-3 rounded border border-[#d4a574]/30 bg-[#d4a574]/10 px-3 py-2 text-[12px] text-[#d4a574]">
            Pendente: {missing.join(", ")}
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
            disabled={saving || !canSubmit}
            title={canSubmit ? undefined : missing.join(", ")}
          >
            {saving ? "Salvando…" : "Salvar"}
          </button>
        </div>
      </div>
    </div>
  );
}
