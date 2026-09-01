"""
Gera PDF colorido (1 página paisagem) com o Gantt textual condensado
para 45 dias da Lousa Digital SINDESTIVA-PE.

Layout: barra colorida no topo de cada linha + bloco de texto livre
(tarefas + marco) abaixo, ocupando toda a largura.
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

# =========================
# Identidade Portuário-Industrial
# =========================
BG_DEEP    = colors.HexColor("#061321")
BG_BASE    = colors.HexColor("#0A1929")
BG_RAISED  = colors.HexColor("#0F2438")
BG_CARD    = colors.HexColor("#122E47")
BORDER     = colors.HexColor("#1E3A52")
BORDER_HI  = colors.HexColor("#2A5070")
TEXT_HI    = colors.HexColor("#E8EEF4")
TEXT_MID   = colors.HexColor("#94A8BD")
TEXT_LOW   = colors.HexColor("#5F7A92")
GOLD       = colors.HexColor("#D4A574")
GOLD_SOFT  = colors.HexColor("#E8C49A")
CYAN       = colors.HexColor("#4FB8C9")
GREEN      = colors.HexColor("#5DBB7D")
AMBER      = colors.HexColor("#E8A33D")
RED        = colors.HexColor("#E04A4A")
PURPLE     = colors.HexColor("#9B7EC4")

CAT_SCOOP  = colors.HexColor("#2C5C8E")
CAT_BUILD  = colors.HexColor("#3A7CB0")
CAT_OPS    = colors.HexColor("#5A9BC9")
CAT_AUDIT  = colors.HexColor("#C4924A")
CAT_LAUNCH = colors.HexColor("#D4A574")

# =========================
# Cronograma (45 dias corridos) — D1 = 14/09/2026
# =========================
SPRINTS = [
    {
        "id": "S0", "label": "Kickoff",
        "start_day": 1, "duration": 5, "color": CAT_SCOOP,
        "tasks": [
            "Reunião Josias + assinatura do termo de aprovação",
            "CCT 2024-2026 + números reais (TPAs, fiscais, turnos/dia)",
            "Parecer LGPD do advogado trabalhista",
            "Setup repo + VPS Hetzner + domínio lousa.pscode.ia.br",
            "Carta formal ao OGMO/PE (Aviso de Recebimento)",
        ],
        "milestone": "M0 · Premissas validadas (gate de entrada da Fase 1)",
    },
    {
        "id": "S1", "label": "Fundação + Scraping",
        "start_day": 6, "duration": 10, "color": CAT_SCOOP,
        "tasks": [
            "Monorepo Turborepo + Postgres 17 + Redis + CI GitHub Actions",
            "Auth NextAuth (CPF+matrícula+OTP) + RBAC + 3 seeds (Paulo/Manoel/José)",
            "Scraper TPA/Suape (Playwright + parser tolerante + alertas de mudança)",
            "Scraper EscalaNet/Recife (HTTPX) + matcher de matrículas",
            "API /lousa e /listagem com snapshots a cada 60s + Swagger",
        ],
        "milestone": "M1 · Centro autenticado · M2 · Lousa oficial espelhada (Suape + Recife)",
    },
    {
        "id": "S2", "label": "PWA do TPA",
        "start_day": 16, "duration": 8, "color": CAT_BUILD,
        "tasks": [
            "PWA instalável (manifest.json + service worker via next-pwa)",
            "Login CPF + matrícula + OTP WhatsApp (Evolution API)",
            "Telas: Início / Escala / Histórico / Perfil + LGPD Art. 18",
            "Confirmação de presença + push FCM + deep link WhatsApp Fiscal",
            "IndexedDB offline (escala fica acessível sem 4G) + Lighthouse ≥ 90",
        ],
        "milestone": "M3 · PWA instalável e funcional (escala offline + push < 30s)",
    },
    {
        "id": "S3", "label": "Centro de Comando · Lousa",
        "start_day": 24, "duration": 8, "color": CAT_BUILD,
        "tasks": [
            "Layout dark portuário-industrial (header + sidebar + breadcrumbs)",
            "Tabela 26 col × 11 fainas × 2 turnos × 2 portos com agrupamento por categoria",
            "4 KPIs (escalados, presença %, remanejamentos hoje, sync OGMO)",
            "WebSocket live update (< 1s) + switcher Porto/Turno + fila OGMO lateral",
            "Click em ponteiro → modal de remanejamento pré-preenchido com contexto",
        ],
        "milestone": "M4 · Centro mostra lousa oficial em tempo real (web + WebSocket)",
    },
    {
        "id": "S4", "label": "Remanejamento + OGMO",
        "start_day": 32, "duration": 6, "color": CAT_OPS,
        "tasks": [
            "Modal completo (motivo + base legal CCT + ack obrigatório)",
            "Hash chain SHA-256 no momento da criação (cada evento encadeia o anterior)",
            "E-mail formal ao OGMO via Resend (template HTML + PDF WeasyPrint)",
            "Webhook HMAC-SHA256 preparado + Painel OGMO read-only (token fixo)",
            "Status SENT/PEND/ACK/NACK + retry com backoff 1m/5m/15m",
        ],
        "milestone": "M5 · Remanejamento digital notifica OGMO em < 2 min (e-mail + painel)",
    },
    {
        "id": "S5", "label": "Auditoria + LGPD + BI",
        "start_day": 38, "duration": 5, "color": CAT_AUDIT,
        "tasks": [
            "Trilha append-only + verificador hash chain diário às 03:00",
            "Retenção 24m automática + Art. 18 LGPD (solicitar exclusão)",
            "Dashboard DPO + logs de acesso + export PDF assinado + CSV",
            "BI: 4 dashboards ECharts (comparecimento, ranking, cais, status)",
            "Drill-down por dia + comparativo de períodos (7/30/90/365)",
        ],
        "milestone": "M6 · Auditoria pronta para MPT/ANTAQ · M7 · BI para diretoria/CCT",
    },
    {
        "id": "S6", "label": "Hardening + Homologação",
        "start_day": 43, "duration": 2, "color": CAT_LAUNCH,
        "tasks": [
            "Rate limit (slowapi) + CSRF + Helmet + CSP + CORS restrito",
            "Backup diário 03:00 + k6 p95 < 1s com 50 VUs + Sentry + Uptime Kuma",
            "Treinamento Manoel Costa (presencial 2h) + 1 turno real de homologação",
        ],
        "milestone": "M8 · Hardening verde (zero P0 OWASP) · M9 · Manoel opera sozinho",
    },
    {
        "id": "S7", "label": "Go-Live",
        "start_day": 45, "duration": 1, "color": CAT_LAUNCH,
        "tasks": [
            "Status page verde · Manoel opera 1 turno real com Paulo on-call",
            "Apresentação interna Josias + diretoria + OGMO/PE + MPT-PE + SINDOPE",
            "Início da campanha de instalação do PWA nos TPAs do Suape",
        ],
        "milestone": "M10 · Go-Live · Suape em produção · 100% fiscais operando",
    },
]

# =========================
# Setup canvas
# =========================
PAGE_W, PAGE_H = landscape(A4)
OUT = "/Users/paulosiqueira/Documents/PS-Code/Projetos/SuporteGerencial/SINDESTIVA-PE/SINDESTIVA-PE-VISAO-GERAL-45DIAS.pdf"
c = canvas.Canvas(OUT, pagesize=landscape(A4))

# Background
c.setFillColor(BG_DEEP)
c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

# =========================
# Header
# =========================
HEADER_H = 58
c.setFillColor(BG_BASE)
c.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)
c.setStrokeColor(BORDER)
c.setLineWidth(0.6)
c.line(0, PAGE_H - HEADER_H, PAGE_W, PAGE_H - HEADER_H)

# Brand
c.setFillColor(GOLD)
c.setFont("Helvetica-Bold", 19)
c.drawString(18*mm, PAGE_H - 22, "SE")
c.setFillColor(TEXT_HI)
c.setFont("Helvetica-Bold", 13)
c.drawString(30*mm, PAGE_H - 17, "SINDESTIVA-PE")
c.setFillColor(TEXT_MID)
c.setFont("Helvetica", 8.5)
c.drawString(30*mm, PAGE_H - 28, "Centro de Comando da Lousa Digital")
c.setFillColor(TEXT_LOW)
c.setFont("Helvetica", 7.5)
c.drawString(30*mm, PAGE_H - 38, "Suporte Gerencial · slug: lousa-sindestiva · v1.0")

# Título direito
c.setFillColor(GOLD)
c.setFont("Helvetica-Bold", 15)
c.drawRightString(PAGE_W - 18*mm, PAGE_H - 17, "Visão Geral do Cronograma · 45 dias")
c.setFillColor(TEXT_MID)
c.setFont("Helvetica", 8.5)
c.drawRightString(PAGE_W - 18*mm, PAGE_H - 28, "Cenário Paulo Siqueira full-time · 40h/semana")
c.setFillColor(CYAN)
c.setFont("Helvetica-Oblique", 8)
c.drawRightString(PAGE_W - 18*mm, PAGE_H - 38, "D1 = 14/09/2026 (seg) · D45 = 28/10/2026 (qua) · ~10 sem corridas")

# Faixa dourada
c.setStrokeColor(GOLD)
c.setLineWidth(1.0)
c.line(0, PAGE_H - HEADER_H - 0.3, PAGE_W, PAGE_H - HEADER_H - 0.3)

# =========================
# Layout Gantt
# =========================
GANTT_LEFT = 18 * mm
GANTT_RIGHT = PAGE_W - 18 * mm
GANTT_WIDTH = GANTT_RIGHT - GANTT_LEFT

LABEL_W = 56 * mm
NUM_DAYS = 45
HEADER_DAYS_H = 14
ROW_H = 52
ROW_GAP = 2

day_w = (GANTT_WIDTH - LABEL_W) / NUM_DAYS
GANTT_TOP = PAGE_H - HEADER_H - 6

# ----- Faixa de dias -----
c.setFillColor(BG_RAISED)
c.rect(GANTT_LEFT + LABEL_W, GANTT_TOP - HEADER_DAYS_H, NUM_DAYS * day_w, HEADER_DAYS_H, fill=1, stroke=0)
c.setStrokeColor(BORDER_HI)
c.setLineWidth(0.4)
c.rect(GANTT_LEFT + LABEL_W, GANTT_TOP - HEADER_DAYS_H, NUM_DAYS * day_w, HEADER_DAYS_H, fill=1, stroke=0)

for d in range(1, NUM_DAYS + 1):
    x = GANTT_LEFT + LABEL_W + (d - 1) * day_w
    if d == 1 or d % 5 == 0:
        c.setStrokeColor(BORDER_HI)
        c.setLineWidth(0.4)
        c.line(x, GANTT_TOP, x, GANTT_TOP - HEADER_DAYS_H)
        c.setFillColor(TEXT_HI)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(x + day_w/2, GANTT_TOP - 10, f"D{d}")
    else:
        c.setFillColor(TEXT_LOW)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(x + day_w/2, GANTT_TOP - 10, f"{d}")

# Linhas verticais tracejadas (a cada 5 dias)
c.setStrokeColor(BORDER)
c.setLineWidth(0.3)
c.setDash(1, 2)
total_h = len(SPRINTS) * (ROW_H + ROW_GAP)
for d in range(5, NUM_DAYS + 1, 5):
    x = GANTT_LEFT + LABEL_W + d * day_w
    c.line(x, GANTT_TOP - HEADER_DAYS_H, x, GANTT_TOP - HEADER_DAYS_H - total_h)
c.setDash()

# =========================
# Render das sprints
# =========================
task_style  = ParagraphStyle("tk", fontName="Helvetica", fontSize=6.4, leading=7.8, textColor=TEXT_MID, alignment=0)
mile_style  = ParagraphStyle("mi", fontName="Helvetica-Bold", fontSize=7, leading=8.4, textColor=GOLD, alignment=0)

current_y = GANTT_TOP - HEADER_DAYS_H

for idx, s in enumerate(SPRINTS):
    row_top = current_y
    row_bottom = current_y - ROW_H

    # Zebra
    c.setFillColor(BG_RAISED if idx % 2 == 0 else BG_BASE)
    c.rect(GANTT_LEFT, row_bottom, GANTT_WIDTH, ROW_H, fill=1, stroke=0)

    # Coluna de label
    c.setFillColor(BG_CARD)
    c.rect(GANTT_LEFT, row_bottom, LABEL_W - 2, ROW_H, fill=1, stroke=0)
    c.setFillColor(s["color"])
    c.rect(GANTT_LEFT, row_bottom, 3, ROW_H, fill=1, stroke=0)

    # Header do label: ID + nome do sprint + duração
    c.setFillColor(s["color"])
    c.setFont("Helvetica-Bold", 13)
    c.drawString(GANTT_LEFT + 10, row_bottom + ROW_H - 17, s["id"])

    c.setFillColor(TEXT_HI)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(GANTT_LEFT + 28, row_bottom + ROW_H - 16, s["label"])

    c.setFillColor(s["color"])
    c.setFont("Helvetica-Bold", 8)
    c.drawRightString(GANTT_LEFT + LABEL_W - 12, row_bottom + ROW_H - 16, f'{s["duration"]}d')

    # Sublabel
    c.setFillColor(TEXT_LOW)
    c.setFont("Helvetica", 7)
    c.drawString(GANTT_LEFT + 10, row_bottom + ROW_H - 29, f'D{s["start_day"]} → D{s["start_day"]+s["duration"]-1}')

    # ----- Barra do Gantt (no topo da linha, à direita do label) -----
    bar_x = GANTT_LEFT + LABEL_W + (s["start_day"] - 1) * day_w
    bar_w = s["duration"] * day_w
    bar_h = 12
    bar_y = row_bottom + ROW_H - 14

    # sombra
    c.setFillColor(colors.HexColor("#04101A"))
    c.rect(bar_x + 0.7, bar_y - 0.7, bar_w, bar_h, fill=1, stroke=0)
    # barra
    c.setFillColor(s["color"])
    c.rect(bar_x, bar_y, bar_w, bar_h, fill=1, stroke=0)
    # highlight topo
    c.setStrokeColor(colors.HexColor("#FFFFFF"))
    c.setLineWidth(0.5)
    c.line(bar_x, bar_y + bar_h, bar_x + bar_w, bar_y + bar_h)
    # ID dentro da barra
    c.setFillColor(BG_DEEP)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(bar_x + 4, bar_y + 2.2, s["id"])
    # duração dentro da barra (à direita)
    if bar_w > 30:
        c.setFillColor(BG_DEEP)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawRightString(bar_x + bar_w - 4, bar_y + 2.2, f'{s["duration"]}d')

    # ----- Bloco de tarefas: texto embaixo da barra, ocupando toda a largura -----
    tasks_text = "  ·  ".join(s["tasks"])
    p_t = Paragraph(tasks_text, task_style)
    avail_w = GANTT_WIDTH - 6
    avail_h = 18
    w_t, h_t = p_t.wrap(avail_w, avail_h)
    p_t.drawOn(c, GANTT_LEFT + 4, bar_y - h_t - 2)

    # ----- Marco: texto em dourado, na base da linha -----
    p_m = Paragraph("◆ " + s["milestone"], mile_style)
    w_m, h_m = p_m.wrap(avail_w, 10)
    p_m.drawOn(c, GANTT_LEFT + 4, row_bottom + 4)

    current_y -= (ROW_H + ROW_GAP)

# =========================
# Legenda de cores (faixa fina)
# =========================
LEGEND_Y = current_y - 6
LEGEND_H = 16
c.setFillColor(BG_CARD)
c.rect(GANTT_LEFT, LEGEND_Y - LEGEND_H, GANTT_WIDTH, LEGEND_H, fill=1, stroke=0)
c.setStrokeColor(BORDER)
c.setLineWidth(0.4)
c.rect(GANTT_LEFT, LEGEND_Y - LEGEND_H, GANTT_WIDTH, LEGEND_H, fill=1, stroke=0)

c.setFillColor(GOLD)
c.setFont("Helvetica-Bold", 7.5)
c.drawString(GANTT_LEFT + 6, LEGEND_Y - 6, "Categorias:")

legend_items = [
    ("Fundação/Infra",  CAT_SCOOP),
    ("Construção",       CAT_BUILD),
    ("Operação/OGMO",    CAT_OPS),
    ("Auditoria/LGPD",   CAT_AUDIT),
    ("Go-Live",          CAT_LAUNCH),
    ("◆ Marco (M0-M10)", GOLD),
]
lx = GANTT_LEFT + 50
for label, col in legend_items:
    c.setFillColor(col)
    c.rect(lx, LEGEND_Y - 5, 8, 5, fill=1, stroke=0)
    c.setFillColor(TEXT_MID)
    c.setFont("Helvetica", 7)
    c.drawString(lx + 11, LEGEND_Y - 5, label)
    lx += 80

# =========================
# KPIs (faixa inferior)
# =========================
KPI_BAND_Y = LEGEND_Y - LEGEND_H - 6
KPI_H = 28
kpis = [
    ("8 sprints",                 GOLD,    "S0 → S7"),
    ("45 dias corridos",          CYAN,    "14/09 → 28/10/2026"),
    ("~360h Paulo (40h/sem)",     GREEN,   "dedicação full-time"),
    ("R$ 6.030 cash ano 1",       AMBER,   "infra + jurídico + viagem"),
    ("11 marcos M0-M10",          PURPLE,  "gates de qualidade"),
    ("9 épicos · 86 HUs",         TEXT_HI, "WBS estimada"),
]
kpi_w = GANTT_WIDTH / len(kpis)
for i, (txt, col, sub) in enumerate(kpis):
    kx = GANTT_LEFT + i * kpi_w
    c.setFillColor(BG_CARD)
    c.rect(kx + 3, KPI_BAND_Y - KPI_H, kpi_w - 6, KPI_H, fill=1, stroke=0)
    c.setFillColor(col)
    c.rect(kx + 3, KPI_BAND_Y - 2, kpi_w - 6, 2, fill=1, stroke=0)
    c.setFillColor(col)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawCentredString(kx + kpi_w/2, KPI_BAND_Y - 15, txt)
    c.setFillColor(TEXT_MID)
    c.setFont("Helvetica", 7)
    c.drawCentredString(kx + kpi_w/2, KPI_BAND_Y - 25, sub)

# =========================
# Rodapé
# =========================
FOOT_H = 18
c.setFillColor(BG_BASE)
c.rect(0, 0, PAGE_W, FOOT_H, fill=1, stroke=0)
c.setStrokeColor(BORDER)
c.setLineWidth(0.4)
c.line(0, FOOT_H, PAGE_W, FOOT_H)

c.setFillColor(TEXT_LOW)
c.setFont("Helvetica", 7)
c.drawString(18*mm, 11, "SINDESTIVA-PE-VISAO-GERAL-45DIAS.pdf · v1.0 · 01/09/2026")
c.drawString(18*mm, 4, "Base: SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md")

c.setFillColor(GOLD)
c.setFont("Helvetica-Bold", 7.5)
c.drawRightString(PAGE_W - 18*mm, 11, "Cliente: SINDESTIVA-PE · Josias Martins Santiago")
c.setFillColor(TEXT_MID)
c.setFont("Helvetica", 7)
c.drawRightString(PAGE_W - 18*mm, 4, "Aguardando aprovação para Sprint 0 em 14/09/2026")

c.showPage()
c.save()
print(f"PDF gerado: {OUT}")
