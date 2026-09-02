"use client";

import { useEffect, useState } from "react";

// =============================================================================
// SINDESTIVA-PE · PWA do TPA (Sprint 0)
// Mobile-first, dark, portuário-industrial. Consome /api/v1/lousa/public/tpa
// Sem auth no Sprint 0. Em prod vira CPF + matrícula OGMO + OTP WhatsApp.
// =============================================================================

interface ProximoDia {
  data: string; dia_semana: string; turno: string | null;
  funcao: string | null; cais: string | null; escalado: boolean;
}
interface TpaEscala {
  tpa: { id: string; matricula: string; nome: string; categoria: string; funcao_base: string | null; };
  hoje: { data: string; dia_semana: string; turno: string | null; celula: any; escalado: boolean; };
  proximos_7_dias: ProximoDia[];
  stats_7d: { engajamentos: number; faltas: number; recebimentos_brl: number; posicao_rodizio: number; };
  links: { fiscal_whatsapp: string; cct_pdf: string; };
}

const MATRICULAS_DEMO = [
  "0000000000", "OG-0036", "OG-101D", "OG-177B", "OG-31C9",
];

export default function HomePage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const [matricula, setMatricula] = useState(MATRICULAS_DEMO[1]);
  const [data, setData] = useState<TpaEscala | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`${apiUrl}/api/v1/lousa/public/tpa/${matricula}/escala`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => { if (!cancelled) { setData(d); setLoading(false); } })
      .catch((e) => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [apiUrl, matricula]);

  const primeiroNome = data?.tpa.nome?.split(" ")[0] ?? "TPA";
  const cell = data?.hoje.celula;
  const stats = data?.stats_7d;

  return (
    <div className="phone-frame">
      <div className="phone-screen">
        {/* STATUS BAR (fake) */}
        <div className="phone-statusbar">
          <span>07:16</span>
          <span>📶 4G · 100%</span>
        </div>

        {/* HEADER */}
        <div className="phone-header">
          <div className="phone-greeting">Bom dia,</div>
          <div className="phone-name">{primeiroNome} ⚓</div>
          <div className="phone-balance">
            Matrícula {data?.tpa.matricula ?? "—"} · {data?.tpa.categoria ?? "—"}
          </div>
        </div>

        {/* DEMO SELECTOR (só Sprint 0) */}
        <div style={{ padding: "8px 16px", background: "var(--bg-raised)", borderBottom: "1px solid var(--border-soft)" }}>
          <label style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.5 }}>
            🎭 Demo: simular TPA
          </label>
          <select
            value={matricula}
            onChange={(e) => setMatricula(e.target.value)}
            style={{
              display: "block", width: "100%", marginTop: 4, padding: "6px 8px",
              background: "var(--bg-card)", color: "var(--text-primary)",
              border: "1px solid var(--border-soft)", borderRadius: 4, fontSize: 12,
              fontFamily: "JetBrains Mono, monospace",
            }}
          >
            {MATRICULAS_DEMO.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        {/* BODY */}
        <div className="phone-body">
          {loading && <div className="loading">Carregando…</div>}
          {error && <div className="error-box">Erro: {error}</div>}

          {data && (
            <>
              {/* CARD HOJE */}
              {data.hoje.escalado && cell ? (
                <div className="tpa-card highlight">
                  <div className="tpa-card-title">
                    <span className="pulse" /> VOCÊ ESTÁ ESCALADO HOJE
                  </div>
                  <div className="tpa-card-value">{cell.funcao ?? "—"}</div>
                  <div className="tpa-card-sub">
                    {cell.cais ?? "—"} · Turno {data.hoje.turno?.replace("DIURNO ", "") ?? "—"}
                  </div>
                  <button className="tpa-btn" style={{ marginTop: 12 }}>
                    ✓ Confirmar Presença
                  </button>
                </div>
              ) : (
                <div className="tpa-card" style={{ borderColor: "var(--accent-amber)" }}>
                  <div className="tpa-card-title" style={{ color: "var(--accent-amber)" }}>
                    ⚠ VOCÊ NÃO ESTÁ ESCALADO HOJE
                  </div>
                  <div className="tpa-card-sub">Aproveite o dia de folga.</div>
                </div>
              )}

              {/* PRÓXIMA CHAMADA */}
              <div className="tpa-card">
                <div className="tpa-card-title">⏱ PRÓXIMA CHAMADA</div>
                <div className="tpa-card-value">14:00</div>
                <div className="tpa-card-sub">6h 44min restantes · {data.tpa.funcao_base ?? "—"}</div>
              </div>

              {/* PRÓXIMOS 7 DIAS */}
              <div className="tpa-card">
                <div className="tpa-card-title">📅 PRÓXIMOS 7 DIAS</div>
                <div className="next-days">
                  {data.proximos_7_dias.map((d) => (
                    <div key={d.data} className={`next-day ${d.escalado ? "on" : "off"}`}>
                      <div className="day-name">{d.dia_semana}</div>
                      <div className="day-num">{new Date(d.data + "T12:00:00").getDate()}</div>
                      <div className="day-tag">{d.escalado ? "⛴" : "—"}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* ÚLTIMOS 7 DIAS */}
              <div className="tpa-card">
                <div className="tpa-card-title">📊 SEUS ÚLTIMOS 7 DIAS</div>
                <div className="tpa-row"><span className="label">Engajamentos</span><span className="value">{stats?.engajamentos ?? 0}/7</span></div>
                <div className="tpa-row"><span className="label">Faltas</span><span className="value">{stats?.faltas ?? 0}</span></div>
                <div className="tpa-row"><span className="label">Recebimentos</span><span className="value">R$ {(stats?.recebimentos_brl ?? 0).toFixed(2)}</span></div>
                <div className="tpa-row"><span className="label">Posição rodízio</span><span className="value">{stats?.posicao_rodizio ?? "—"}º</span></div>
              </div>

              {/* AÇÕES */}
              <a className="tpa-btn ghost" href={data.links.fiscal_whatsapp} target="_blank" rel="noreferrer">
                💬 Falar com o Fiscal
              </a>
              <button className="tpa-btn ghost" style={{ marginTop: 8 }}>
                📜 Ver CCT completa
              </button>
            </>
          )}
        </div>

        {/* BOTTOM NAV */}
        <div className="phone-nav">
          <button className="phone-nav-item active">Início</button>
          <button className="phone-nav-item">Escala</button>
          <button className="phone-nav-item">Histórico</button>
          <button className="phone-nav-item">Perfil</button>
        </div>
      </div>
    </div>
  );
}
