// =============================================================================
// SINDESTIVA-PE · Mock data para o Centro de Comando
// Usado quando a API está offline (modo dev Sprint 0/1, antes do scraper real).
//
// Layout segue fielmente o protótipo HTML (SINDESTIVA-PE-PROTOTIPO.html
// linhas 1977-2010): 11 fainas × 26 funções × 2 turnos × 2 portos.
//
// TODOs Sprint 2 (scraping):
//   - Substituir `gerarMatriculaMock` por `tpa.matricula_ogmo` real do banco.
//   - Substituir `gerarNomeMock` por `tpa.nome_completo` real.
//   - Quando S2-06 (endpoint /api/lousa) fechar, este arquivo vira
//     fallback opcional de demo.
//
// Nomes são fictícios (rotação determinística baseada em índice). Nenhum
// dado pessoal real é exposto.
// =============================================================================

import type { Porto, Turno } from "@sindestiva/shared";
import type {
  Faina,
  Funcao,
  LousaCellOut,
  LousaPreviewResponse,
  LousaSnapshotOut,
  RemanejamentoItem,
  OgmoNotificacao,
  AuditEvent,
  UserSession,
  FuncaoCategoria,
  FainaCategoria,
} from "./tipos";

// ---- Fainas (catálogo estático do seed) ----------------------------------

export const FAINAS_MOCK: Faina[] = [
  { id: "f-01", codigo: "PRODUCAO",    nome: "Produção",     cor_hex: "#2563eb", ordem: 1 },
  { id: "f-02", codigo: "SALARIO",     nome: "Salário",      cor_hex: "#16a34a", ordem: 2 },
  { id: "f-03", codigo: "SACARIA",     nome: "Sacaria",      cor_hex: "#ca8a04", ordem: 3 },
  { id: "f-04", codigo: "VEICULO",     nome: "Veículo",      cor_hex: "#9333ea", ordem: 4 },
  { id: "f-05", codigo: "DIVERSOS",    nome: "Diversos",     cor_hex: "#64748b", ordem: 5 },
  { id: "f-06", codigo: "CADASTRO",    nome: "Cadastro",     cor_hex: "#0891b2", ordem: 6 },
  { id: "f-07", codigo: "SUPLEMENTAR", nome: "Suplementar",  cor_hex: "#db2777", ordem: 7 },
  { id: "f-08", codigo: "ALTURA",      nome: "Altura NR-35", cor_hex: "#ea580c", ordem: 8 },
  { id: "f-09", codigo: "RO-RO-LEVE",  nome: "Ro-Ro Leve",   cor_hex: "#9333ea", ordem: 9 },
  { id: "f-10", codigo: "RO-RO-PESADO",nome: "Ro-Ro Pesado", cor_hex: "#9333ea", ordem: 10 },
  { id: "f-11", codigo: "EMPILHADOR",  nome: "Empilhador",   cor_hex: "#0891b2", ordem: 11 },
];

// ---- Funções (26 = 6 Mando + 6 Terno + 12 Técnica + 2 Vigia) ------------

export const FUNCOES_MOCK: Funcao[] = [
  // Mando (6)
  { id: "fn-01", codigo: "CM_GERAL",     nome: "C/M Geral",     categoria: "MANDO",   ordem: 1 },
  { id: "fn-02", codigo: "CM_PORAO",     nome: "C/M Porão",     categoria: "MANDO",   ordem: 2 },
  { id: "fn-03", codigo: "CM_BLOCO",     nome: "C/M Bloco",     categoria: "MANDO",   ordem: 3 },
  { id: "fn-04", codigo: "CM_RECHEGO",   nome: "C/M Rechego",   categoria: "MANDO",   ordem: 4 },
  { id: "fn-05", codigo: "CM_CONS",      nome: "C/M Cons.",     categoria: "MANDO",   ordem: 5 },
  { id: "fn-06", codigo: "SUPERVISOR",   nome: "Supervisor",    categoria: "MANDO",   ordem: 6 },
  // Terno (6)
  { id: "fn-07", codigo: "PORAO",        nome: "Porão",         categoria: "TERNO",   ordem: 7 },
  { id: "fn-08", codigo: "BLOCO_MAX",    nome: "Bloco MAX",     categoria: "TERNO",   ordem: 8 },
  { id: "fn-09", codigo: "BLOCO",        nome: "Bloco",         categoria: "TERNO",   ordem: 9 },
  { id: "fn-10", codigo: "RECHEGO",      nome: "Rechego",       categoria: "TERNO",   ordem: 10 },
  { id: "fn-11", codigo: "CONS",         nome: "Cons.",         categoria: "TERNO",   ordem: 11 },
  { id: "fn-12", codigo: "SHIP_LOADER",  nome: "Ship Loader",   categoria: "TERNO",   ordem: 12 },
  // Técnica (12)
  { id: "fn-13", codigo: "SINALEIRO",    nome: "Sinaleiro",     categoria: "TECNICA", ordem: 13 },
  { id: "fn-14", codigo: "GUINCHO_A",    nome: "Guincho A",     categoria: "TECNICA", ordem: 14 },
  { id: "fn-15", codigo: "GUINCHO_B",    nome: "Guincho B",     categoria: "TECNICA", ordem: 15 },
  { id: "fn-16", codigo: "EMP_GP",       nome: "Emp. GP",       categoria: "TECNICA", ordem: 16 },
  { id: "fn-17", codigo: "EMP_PP",       nome: "Emp. PP",       categoria: "TECNICA", ordem: 17 },
  { id: "fn-18", codigo: "V_PESADO",     nome: "V. Pesado",     categoria: "TECNICA", ordem: 18 },
  { id: "fn-19", codigo: "V_LEVE",       nome: "V. Leve",       categoria: "TECNICA", ordem: 19 },
  { id: "fn-20", codigo: "MANOBRISTA",   nome: "Manobrista",    categoria: "TECNICA", ordem: 20 },
  { id: "fn-21", codigo: "TRANSP",       nome: "Transp.",       categoria: "TECNICA", ordem: 21 },
  { id: "fn-22", codigo: "PA_MEC",       nome: "Pá Mec.",       categoria: "TECNICA", ordem: 22 },
  { id: "fn-23", codigo: "RETRO_ESC",    nome: "Retro Esc.",    categoria: "TECNICA", ordem: 23 },
  { id: "fn-24", codigo: "PC",           nome: "PC",            categoria: "TECNICA", ordem: 24 },
  // Vigia (2)
  { id: "fn-25", codigo: "RODIZIO",      nome: "Rodízio",       categoria: "VIGIA",   ordem: 25 },
  { id: "fn-26", codigo: "CONTRA_BORDO", nome: "Contra Bordo",  categoria: "VIGIA",   ordem: 26 },
];

// ---- Nomes fictícios (pool determinístico) -------------------------------

const NOMES_TPA = [
  "José Bezerra", "Manoel Costa", "Antônio Silva", "Severino Ramos",
  "Francisco Lima", "João Santos", "Paulo Souza", "Pedro Oliveira",
  "Marcos Pereira", "Luiz Ferreira", "Carlos Almeida", "Raimundo Silva",
  "Edson Barbosa", "Genivaldo Cruz", "José Roberto", "Manoel Florêncio",
  "Antônio Marcos", "Severino Bezerra", "Francisco das Chagas",
  "João Batista", "Paulo Henrique", "Pedro Cavalcanti", "Marcos Antônio",
  "Luiz Carlos", "Carlos Alberto", "Raimundo Nonato", "Edson Carlos",
];

function gerarMatriculaMock(fIdx: number, fnIdx: number, offset = 0): string {
  // 3 dígitos, similar ao protótipo (012, 058, 247, 163).
  const n = (fIdx * 31 + fnIdx * 17 + offset) % 900 + 12;
  return n.toString().padStart(3, "0");
}

function gerarNomeMock(fIdx: number, fnIdx: number): string {
  const i = (fIdx * 13 + fnIdx * 7) % NOMES_TPA.length;
  return NOMES_TPA[i] ?? "TPA";
}

// ---- Cells mock ---------------------------------------------------------

const CAIS = ["1", "2", "3", "4"];

function gerarCellsMock(turno: Turno, dataRef: string): LousaCellOut[] {
  const cells: LousaCellOut[] = [];
  let cellSeq = 0;
  for (const f of FAINAS_MOCK) {
    for (const fn of FUNCOES_MOCK) {
      cellSeq += 1;
      // Densidade: ~80% das células ocupadas.
      const vazio = ((f.ordem * 7 + fn.ordem) % 5 === 0) && (turno === "NOTURNO" ? fn.ordem % 2 === 0 : fn.ordem % 3 === 0);
      // Status: 5% AUSENTE, 3% REMANEJADO, 2% CONFIRMADO.
      const statusRoll = (f.ordem * 11 + fn.ordem * 3) % 100;
      const status: LousaCellOut["status"] = vazio
        ? "NORMAL"
        : statusRoll < 5
          ? "AUSENTE"
          : statusRoll < 8
            ? "REMANEJADO"
            : statusRoll < 10
              ? "CONFIRMADO"
              : "NORMAL";

      // Se vazio, TPA é null.
      if (vazio) {
        cells.push({
          id: `cell-${cellSeq}`,
          faina_id: f.id,
          funcao_id: fn.id,
          cais: null,
          navio_id: null,
          tpa_id: null,
          tpa_nome: null,
          tpa_matricula: null,
          status: "NORMAL",
          data_referencia: dataRef,
        });
        continue;
      }

      const cais = CAIS[(f.ordem + fn.ordem) % CAIS.length] ?? "1";
      cells.push({
        id: `cell-${cellSeq}`,
        faina_id: f.id,
        funcao_id: fn.id,
        cais,
        navio_id: null,
        tpa_id: `tpa-${f.ordem}-${fn.ordem}`,
        tpa_nome: gerarNomeMock(f.ordem, fn.ordem),
        tpa_matricula: gerarMatriculaMock(f.ordem, fn.ordem),
        status,
        data_referencia: dataRef,
      });
    }
  }
  return cells;
}

// ---- Lousa mock ----------------------------------------------------------

export function getMockLousaPreview(porto: Porto, turno: Turno): LousaPreviewResponse {
  const dataRef = new Date().toISOString().slice(0, 10);
  const cells = gerarCellsMock(turno, dataRef);
  const totalTpas = cells.filter((c) => c.tpa_id !== null).length;
  const snapshot: LousaSnapshotOut = {
    id: `mock-snap-${porto}-${turno}`,
    scraped_at: new Date().toISOString(),
    status: "OK",
    total_celulas: cells.length,
    total_tpas_escalados: totalTpas,
    html_hash_sha256: "0000000000000000000000000000000000000000000000000000000000000000",
  };
  return {
    porto: { id: `p-${porto}`, codigo: porto, nome: porto === "SUAPE" ? "Porto de Suape" : "Porto do Recife" },
    turno: { id: `t-${turno}`, codigo: turno, nome: turno === "DIURNO" ? "Diurno 08-16" : "Noturno 20-04" },
    snapshot,
    fainas: FAINAS_MOCK,
    funcoes: FUNCOES_MOCK,
    cells,
    stats: {
      total_cells: cells.length,
      total_tpas_escalados: totalTpas,
      total_fainas: FAINAS_MOCK.length,
      total_funcoes: FUNCOES_MOCK.length,
    },
  };
}

// ---- Remanejamentos mock (Sprint 5 implementa de verdade) ---------------

export const MOCK_REMANEJAMENTOS: RemanejamentoItem[] = [
  {
    id: "rem-001",
    data_hora: "2026-09-01T07:14:00",
    tpa_removido_nome: "José Bezerra da Silva",
    tpa_removido_matricula: "012",
    funcao_codigo: "GUINCHO_A",
    faina_codigo: "PRODUCAO",
    motivo: "Atestado médico — NR-7",
    base_legal: "CCT 2024-2026 · Cláusula 7ª, §2º",
    status: "PEND",
    created_by: "Manoel Costa (Fiscal)",
    tpa_substituto_nome: "Paulo Henrique",
    hash_evento: "a1b2c3d4e5f6...",
  },
  {
    id: "rem-002",
    data_hora: "2026-09-01T06:58:00",
    tpa_removido_nome: "Manoel Florêncio",
    tpa_removido_matricula: "247",
    funcao_codigo: "EMP_GP",
    faina_codigo: "EMPILHADOR",
    motivo: "Trocou p/ turno noturno",
    base_legal: "CCT 2024-2026 · Cláusula 5ª",
    status: "SENT",
    created_by: "Manoel Costa (Fiscal)",
    tpa_substituto_nome: "Francisco das Chagas",
    hash_evento: "b2c3d4e5f6a7...",
  },
  {
    id: "rem-003",
    data_hora: "2026-09-01T06:42:00",
    tpa_removido_nome: "Antônio José da Silva",
    tpa_removido_matricula: "058",
    funcao_codigo: "CM_GERAL",
    faina_codigo: "PRODUCAO",
    motivo: "Reforço de terno — navio extra",
    base_legal: "CCT 2024-2026 · Cláusula 7ª, §3º",
    status: "SENT",
    created_by: "Manoel Costa (Fiscal)",
    tpa_substituto_nome: "Marcos Antônio",
    hash_evento: "c3d4e5f6a7b8...",
  },
  {
    id: "rem-004",
    data_hora: "2026-09-01T06:30:00",
    tpa_removido_nome: "Severino Ramos",
    tpa_removido_matricula: "163",
    funcao_codigo: "SINALEIRO",
    faina_codigo: "SUPLEMENTAR",
    motivo: "Substituição rotina",
    base_legal: "CCT 2024-2026 · Cláusula 7ª, §1º",
    status: "ACK",
    created_by: "Manoel Costa (Fiscal)",
    tpa_substituto_nome: "João Batista",
    hash_evento: "d4e5f6a7b8c9...",
  },
];

// ---- OGMO mock ----------------------------------------------------------

export const MOCK_OGMO: OgmoNotificacao[] = [
  {
    id: "ogmo-001",
    data_hora: "2026-09-01T07:14:30",
    remanejamento_id: "rem-001",
    canal: "EMAIL",
    destinatario: "escala@ogmo-pe.com.br",
    status: "SENT",
    tentativas: 1,
  },
  {
    id: "ogmo-002",
    data_hora: "2026-09-01T07:00:15",
    remanejamento_id: "rem-002",
    canal: "EMAIL",
    destinatario: "escala@ogmo-pe.com.br",
    status: "ACK",
    tentativas: 1,
  },
  {
    id: "ogmo-003",
    data_hora: "2026-09-01T06:45:08",
    remanejamento_id: "rem-003",
    canal: "WEBHOOK",
    destinatario: "https://ogmo-pe.com.br/webhook/sindestiva",
    status: "PEND",
    tentativas: 3,
    ultimo_erro: "Timeout 5s — endpoint recusando conexão (Risco R1 do plano).",
  },
];

// ---- Auditoria mock (Sprint 6 implementa de verdade) --------------------

export const MOCK_AUDIT: AuditEvent[] = [
  {
    id: "evt-004",
    created_at: "2026-09-01T07:30:00",
    kind: "OGMO_ACK",
    actor: "escala@ogmo-pe.com.br",
    descricao: "OGMO confirmou remanejamento rem-002 (Manoel Florêncio → Francisco das Chagas).",
    hash_evento: "h4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4ev4",
    hash_anterior: "h3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3",
    verificado: true,
  },
  {
    id: "evt-003",
    created_at: "2026-09-01T07:14:30",
    kind: "REMANEJAMENTO_ENVIADO",
    actor: "Manoel Costa (Fiscal)",
    descricao: "E-mail enviado a escala@ogmo-pe.com.br — Remanejamento rem-001.",
    hash_evento: "h3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3ev3",
    hash_anterior: "h2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2",
    verificado: true,
  },
  {
    id: "evt-002",
    created_at: "2026-09-01T07:14:00",
    kind: "REMANEJAMENTO_CRIADO",
    actor: "Manoel Costa (Fiscal)",
    descricao: "Remanejamento rem-001 criado: José Bezerra → Paulo Henrique (Guincho A · Produção).",
    hash_evento: "h2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2ev2",
    hash_anterior: "h1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1",
    verificado: true,
  },
  {
    id: "evt-001",
    created_at: "2026-09-01T07:00:00",
    kind: "SCRAPING_OK",
    actor: "tpa-scraper (job 6h00)",
    descricao: "Snapshot SUAPE/DIURNO capturado — 142 TPAs, hash OK.",
    hash_evento: "h1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1ev1",
    hash_anterior: "0000000000000000000000000000000000000000000000000000000000000000",
    verificado: true,
  },
];

// ---- Sessão mock (Sprint 1 implementa NextAuth) ------------------------

export const MOCK_SESSION: UserSession = {
  id: "user-paulo",
  nome: "Paulo Siqueira",
  role: "DIRIGENTE",
  email: "paulo@sindestiva-pe.org.br",
};
