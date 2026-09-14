"use client";

import { EmptyState } from "@/app/_components/EmptyState";
import {
  ApiError,
  createAdminTpa,
  listAdminTpas,
  listTpaFuncoes,
  updateAdminTpa,
  type AdminTpa,
  type TpaFuncaoMeta,
} from "@/lib/api";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  emptyTpaFormValues,
  TpaFormModal,
  toCreatePayload,
  toUpdatePayload,
  valuesFromTpa,
  type TpaFormValues,
} from "./_components/tpa-form-modal";
import { TpasTable } from "./_components/tpas-table";

function parseApiError(err: unknown): string {
  if (err instanceof ApiError) {
    try {
      const parsed = JSON.parse(err.detail) as { message?: string; code?: string };
      if (parsed.message) return parsed.message;
    } catch {
      /* detail plain string */
    }
    return err.detail;
  }
  return err instanceof Error ? err.message : "Erro desconhecido";
}

export default function TpasPage(): ReactNode {
  const [items, setItems] = useState<AdminTpa[] | null>(null);
  const [total, setTotal] = useState(0);
  const [funcoes, setFuncoes] = useState<TpaFuncaoMeta[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [editing, setEditing] = useState<AdminTpa | null>(null);
  const [form, setForm] = useState<TpaFormValues>(emptyTpaFormValues());
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    setLoadError(null);
    try {
      const [data, funcoesData] = await Promise.all([listAdminTpas(), listTpaFuncoes()]);
      setItems(data.items);
      setTotal(data.total);
      setFuncoes(funcoesData);
    } catch (err) {
      setLoadError(parseApiError(err));
      setItems([]);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  function openCreate(): void {
    setModalMode("create");
    setEditing(null);
    const next = emptyTpaFormValues();
    if (funcoes[0]) {
      next.funcao_base_id = funcoes[0].id;
    }
    setForm(next);
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(tpa: AdminTpa): void {
    setModalMode("edit");
    setEditing(tpa);
    setForm(valuesFromTpa(tpa));
    setFormError(null);
    setModalOpen(true);
  }

  async function onSubmitForm(): Promise<void> {
    setSaving(true);
    setFormError(null);
    try {
      if (modalMode === "create") {
        await createAdminTpa(toCreatePayload(form));
      } else if (editing) {
        await updateAdminTpa(editing.id, toUpdatePayload(form));
      }
      setModalOpen(false);
      await reload();
    } catch (err) {
      setFormError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[#e8eef4]">Cadastro de TPAs</h1>
          <p className="mt-1 text-[13px] text-[#94a8bd]">
            Trabalhadores portuários avulsos — perfil User(TPA) + cadastro sindical (somente DIRIGENTE).
          </p>
          {total > 0 && (
            <p className="mt-1 text-[12px] text-[#5f7a92]">{total} registro(s)</p>
          )}
        </div>
        <button
          type="button"
          className="rounded bg-[#d4a574] px-4 py-2 text-[13px] font-semibold text-[#0a1929] hover:bg-[#e0b585]"
          onClick={openCreate}
        >
          + Novo TPA
        </button>
      </div>

      {loadError && (
        <div className="mb-4 rounded border border-[#e04a4a]/40 bg-[#e04a4a]/10 px-4 py-3 text-[13px] text-[#e04a4a]">
          {loadError}
        </div>
      )}

      {items === null ? (
        <EmptyState title="Carregando TPAs…" description="" />
      ) : (
        <TpasTable items={items} onEdit={openEdit} />
      )}

      <TpaFormModal
        open={modalOpen}
        mode={modalMode}
        values={form}
        funcoes={funcoes}
        saving={saving}
        error={formError}
        onChange={setForm}
        onClose={() => setModalOpen(false)}
        onSubmit={() => void onSubmitForm()}
      />
    </div>
  );
}
