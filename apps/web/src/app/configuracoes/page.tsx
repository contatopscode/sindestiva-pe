"use client";

import {
  getConfiguracoes,
  updateConfiguracoes,
  type ConfiguracoesResponse,
} from "@/lib/api";
import { parseApiError } from "@/lib/parse-api-error";
import { useToast } from "@/lib/toast";
import { useCallback, useEffect, useState, type ReactNode } from "react";

function formatWhatsappDisplay(e164: string | null): string {
  if (!e164) return "";
  if (e164.length === 13 && e164.startsWith("55")) {
    const ddd = e164.slice(2, 4);
    const rest = e164.slice(4);
    return `+55 (${ddd}) ${rest.slice(0, 5)}-${rest.slice(5)}`;
  }
  return e164;
}

export default function ConfiguracoesPage(): ReactNode {
  const [config, setConfig] = useState<ConfiguracoesResponse | null>(null);
  const [input, setInput] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const reload = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await getConfiguracoes();
      setConfig(data);
      setInput(data.ogmo_whatsapp ?? "");
    } catch (err) {
      setLoadError(parseApiError(err));
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onSave(): Promise<void> {
    setSaving(true);
    try {
      const data = await updateConfiguracoes(input.trim());
      setConfig(data);
      setInput(data.ogmo_whatsapp ?? "");
      toast.showSuccess("WhatsApp do OGMO salvo.");
    } catch (err) {
      toast.showError(parseApiError(err));
    } finally {
      setSaving(false);
    }
  }

  const fonteLabel =
    config?.ogmo_whatsapp_fonte === "db"
      ? "banco de dados"
      : config?.ogmo_whatsapp_fonte === "env"
        ? "variável de ambiente (fallback)"
        : "não configurado";

  return (
    <div className="p-6 max-w-xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-[#e8eef4]">Configurações</h1>
        <p className="mt-1 text-[13px] text-[#94a8bd]">
          Número WhatsApp do OGMO/PE para notificações formais de remanejamento (somente DIRIGENTE).
        </p>
      </div>

      {loadError && (
        <div className="error-box mb-4">
          ❌ {loadError}
        </div>
      )}

      {config && !config.evolution_configured && (
        <div className="mb-4 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-[12px] text-amber-200">
          Evolution API não está configurada no servidor (URL/KEY). O número pode ser salvo, mas o
          envio WhatsApp falhará até a infra ser provisionada.
        </div>
      )}

      <div className="rounded-lg border border-[#1e3a52] bg-[#0f2438] p-4 space-y-4">
        <div>
          <label htmlFor="ogmo-whatsapp" className="block text-[11px] font-bold uppercase text-[#94a8bd]">
            WhatsApp OGMO
          </label>
          <p className="mt-1 text-[11px] text-[#5f7a92]">
            Formato BR com DDD — ex.: (81) 99999-0001. Será normalizado para E.164 (5581…).
          </p>
          <input
            id="ogmo-whatsapp"
            type="tel"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="81999990001"
            className="mt-2 w-full rounded border border-[#2a5070] bg-[#0a1929] px-3 py-2 text-[13px] text-[#e8eef4]"
          />
          {config?.ogmo_whatsapp && (
            <p className="mt-2 text-[11px] text-[#94a8bd]">
              Atual: {formatWhatsappDisplay(config.ogmo_whatsapp)} · fonte: {fonteLabel}
            </p>
          )}
        </div>

        <button
          type="button"
          disabled={saving || !input.trim()}
          onClick={() => void onSave()}
          className="rounded bg-[#d4a574] px-4 py-2 text-[13px] font-semibold text-[#0a1929] hover:bg-[#e0b585] disabled:opacity-50"
        >
          {saving ? "Salvando…" : "Salvar"}
        </button>
      </div>

      <p className="mt-4 text-[11px] text-[#5f7a92]">
        Credenciais Evolution (URL, instância Vigilia, API key) permanecem apenas no ambiente do
        servidor — não são editáveis aqui.
      </p>
    </div>
  );
}
