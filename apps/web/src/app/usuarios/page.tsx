"use client";

import { EmptyState } from "@/app/_components/EmptyState";
import {
  createAdminUser,
  listAdminUsers,
  updateAdminUser,
  type AdminUser,
} from "@/lib/api";
import { parseApiError } from "@/lib/parse-api-error";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { userFormMissingFields } from "./_components/user-form-validation";
import {
  emptyFormValues,
  toCreatePayload,
  toUpdatePayload,
  UserFormModal,
  valuesFromUser,
  type UserFormValues,
} from "./_components/user-form-modal";
import { UsersTable } from "./_components/users-table";

export default function UsuariosPage(): ReactNode {
  const [items, setItems] = useState<AdminUser[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [form, setForm] = useState<UserFormValues>(emptyFormValues());
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await listAdminUsers();
      setItems(data.items);
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
    setForm(emptyFormValues("FISCAL"));
    setFormError(null);
    setModalOpen(true);
  }

  function openEdit(user: AdminUser): void {
    setModalMode("edit");
    setEditing(user);
    setForm(valuesFromUser(user));
    setFormError(null);
    setModalOpen(true);
  }

  async function onSubmitForm(): Promise<void> {
    const missing = userFormMissingFields(form, modalMode);
    if (missing.length > 0) {
      setFormError(`Preencha os campos obrigatórios: ${missing.join(", ")}`);
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      if (modalMode === "create") {
        await createAdminUser(toCreatePayload(form));
      } else if (editing) {
        await updateAdminUser(editing.id, toUpdatePayload(form));
      }
      setModalOpen(false);
      await reload();
    } catch (err) {
      setFormError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function onToggleActive(user: AdminUser): Promise<void> {
    setBusyId(user.id);
    try {
      const nextStatus = user.status === "ATIVO" ? "INATIVO" : "ATIVO";
      await updateAdminUser(user.id, { status: nextStatus });
      await reload();
    } catch (err) {
      setLoadError(parseApiError(err));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-[#e8eef4]">Gestão de usuários</h1>
          <p className="mt-1 text-[13px] text-[#94a8bd]">
            Fiscais e dirigentes — cadastro, edição e ativação (somente DIRIGENTE).
          </p>
        </div>
        <button
          type="button"
          className="rounded bg-[#d4a574] px-4 py-2 text-[13px] font-semibold text-[#0a1929] hover:bg-[#e0b585]"
          onClick={openCreate}
        >
          + Novo usuário
        </button>
      </div>

      {loadError && (
        <div className="mb-4 rounded border border-[#e04a4a]/40 bg-[#e04a4a]/10 px-4 py-3 text-[13px] text-[#e04a4a]">
          {loadError}
        </div>
      )}

      {items === null ? (
        <EmptyState title="Carregando usuários…" description="" />
      ) : (
        <UsersTable
          items={items}
          busyId={busyId}
          onEdit={openEdit}
          onToggleActive={(u) => void onToggleActive(u)}
        />
      )}

      <UserFormModal
        open={modalOpen}
        mode={modalMode}
        values={form}
        saving={saving}
        error={formError}
        onChange={setForm}
        onClose={() => setModalOpen(false)}
        onSubmit={() => void onSubmitForm()}
      />
    </div>
  );
}
