// =============================================================================
// SINDESTIVA-PE · /navios — catálogo de navios (issue #15)
// Destino do redirect após salvar em /navios/novo.
// =============================================================================

"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { listarNavios, mensagemErroNavio, type Navio } from "@/lib/navios";
import { ROTULO_TIPO_OPERACAO, type TipoOperacao } from "@/lib/schemas/navio";

export default function NaviosPage(): ReactNode {
  const [navios, setNavios] = useState<Navio[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    let ativo = true;
    listarNavios()
      .then((r) => ativo && setNavios(r.items))
      .catch((e) => ativo && setErro(mensagemErroNavio(e)))
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, []);

  return (
    <div className="p-6">
      <div className="section-header">
        <div>
          <h1 className="section-title">Navios</h1>
          <p className="section-subtitle">Catálogo usado na lousa e nos relatórios de BI.</p>
        </div>
        <Link
          href="/navios/novo"
          className="rounded bg-[#d4a574] px-4 py-2 text-[12px] font-bold text-[#0a1929] hover:bg-[#e8c49a]"
        >
          + Novo navio
        </Link>
      </div>

      {erro && (
        <div
          role="alert"
          className="mb-4 rounded border border-[#7d2e2e] bg-[#251010] px-4 py-3 text-[13px] text-[#f2a3a3]"
        >
          ⚠️ {erro}
        </div>
      )}

      {carregando ? (
        <div className="loading">Carregando…</div>
      ) : navios.length === 0 ? (
        <p className="text-[13px] text-[#8fa8c0]">Nenhum navio cadastrado ainda.</p>
      ) : (
        <table className="w-full text-left text-[13px]">
          <thead className="text-[12px] uppercase text-[#8fa8c0]">
            <tr>
              <th className="py-2">Nome</th>
              <th className="py-2">IMO</th>
              <th className="py-2">Bandeira</th>
              <th className="py-2">Operação</th>
            </tr>
          </thead>
          <tbody>
            {navios.map((n) => (
              <tr key={n.id} className="border-t border-[#1e3a5f]">
                <td className="py-2 text-[#e6edf3]">{n.nome}</td>
                <td className="py-2 font-mono text-[#d4a574]">{n.imo ?? "—"}</td>
                <td className="py-2 text-[#8fa8c0]">{n.bandeira ?? "—"}</td>
                <td className="py-2 text-[#8fa8c0]">
                  {n.tipo_operacao
                    ? (ROTULO_TIPO_OPERACAO[n.tipo_operacao as TipoOperacao] ?? n.tipo_operacao)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
