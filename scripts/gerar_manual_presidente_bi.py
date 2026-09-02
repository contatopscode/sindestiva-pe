"""SINDESTIVA-PE · Gera o manual do presidente (T7-10).

PDF de 4 páginas:
  P1: Capa + Como abrir o BI
  P2: 4 KPIs explicados
  P3: Gráfico + top remanejados + cards
  P4: Insights + Export PDF + Suporte

Output: docs/MANUAL-PRESIDENTE-BI.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

from weasyprint import HTML

REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / "docs" / "MANUAL-PRESIDENTE-BI.pdf"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

HTML_DOC = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Manual do Presidente · BI SINDESTIVA-PE</title>
<style>
@page { size: A4; margin: 1.8cm; }
@page :first { margin: 0; }
body { font-family: 'Helvetica', 'Arial', sans-serif; font-size: 10pt; color: #1a2540; line-height: 1.5; }
h1 { color: #ffffff; background: linear-gradient(135deg, #1a2540 0%, #2a5070 100%); padding: 24px; margin: 0; font-size: 28pt; }
h1 .sub { display: block; font-size: 12pt; color: #c8a04d; margin-top: 6px; font-weight: normal; }
h2 { color: #1a2540; border-bottom: 2px solid #c8a04d; padding-bottom: 4px; margin-top: 18px; }
h3 { color: #2a5070; margin-top: 12px; }
.capa { page-break-after: always; padding: 0; margin: 0; height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; background: linear-gradient(135deg, #1a2540 0%, #0a1828 100%); color: white; }
.capa h1 { background: none; font-size: 36pt; }
.capa .versao { color: #c8a04d; font-size: 11pt; margin-top: 24px; }
.capa .dest { color: #94a8bd; font-size: 12pt; margin-top: 6px; }
.page { page-break-after: always; }
.page:last-child { page-break-after: auto; }
.kpi-box { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 12px 0; }
.kpi { border-left: 3px solid #c8a04d; padding: 8px 12px; background: #f3f4f6; }
.kpi .label { font-size: 9pt; text-transform: uppercase; color: #6b7280; font-weight: bold; }
.kpi .value { font-size: 18pt; font-weight: bold; color: #1a2540; }
.kpi .desc { font-size: 8pt; color: #6b7280; margin-top: 4px; }
ol.steps { padding-left: 18px; }
ol.steps li { margin-bottom: 8px; }
.tip { background: #fffbeb; border-left: 3px solid #d97706; padding: 8px 12px; margin: 12px 0; font-size: 9pt; }
table { width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 9pt; }
th, td { padding: 6px 8px; text-align: left; border-bottom: 1px solid #e5e7eb; }
th { background: #1a2540; color: white; }
footer { text-align: center; color: #6b7280; font-size: 8pt; margin-top: 24px; padding-top: 8px; border-top: 1px solid #e5e7eb; }
</style>
</head>
<body>

<!-- PÁGINA 1 — CAPA -->
<section class="capa">
  <h1>Manual do Presidente<br><span class="sub">BI & Dashboards · SINDESTIVA-PE</span></h1>
  <p class="versao">Versão 1.0 · Setembro 2026</p>
  <p class="dest">Para: Josias (Presidente do SINDESTIVA-PE)</p>
  <p class="dest">Sistema: Lousa Digital · Centro de Comando</p>
</section>

<!-- PÁGINA 2 — COMO ABRIR + 4 KPIs -->
<section class="page">
  <h2>1. Como abrir o BI</h2>
  <ol class="steps">
    <li>Abra o navegador e acesse <strong>http://lousa.pscode.ia.br</strong> (ou o link que o Paulo enviou).</li>
    <li>Faça login com seu e-mail <strong>josias@sindestiva-pe.com.br</strong> e sua senha.</li>
    <li>No menu lateral esquerdo, clique em <strong>"BI & Dashboards"</strong> (ícone 📊).</li>
    <li>Pronto! Você verá 4 cartões de KPIs no topo da tela.</li>
  </ol>

  <h2>2. Os 4 KPIs (cartões no topo da tela)</h2>
  <div class="kpi-box">
    <div class="kpi">
      <div class="label">Comparecimento</div>
      <div class="value">87,5%</div>
      <div class="desc">% de TPA que confirmaram presença via PWA no período.</div>
    </div>
    <div class="kpi">
      <div class="label">Folha Paga</div>
      <div class="value">R$ 48.200</div>
      <div class="desc">Estimativa de gasto com remanejamentos (proxy: R$ 25/h × 8h).</div>
    </div>
    <div class="kpi">
      <div class="label">Causa #1 Falta</div>
      <div class="value">ATESTADO_MÉDICO</div>
      <div class="desc">Motivo mais frequente de remanejamento no período.</div>
    </div>
    <div class="kpi">
      <div class="label">% NACK (OGMO)</div>
      <div class="value">3,2%</div>
      <div class="desc">% de notificações rejeitadas pelo OGMO. Alvo: &lt; 10%.</div>
    </div>
  </div>

  <div class="tip">
    💡 <strong>Periodo:</strong> Você pode alternar entre 7, 30, 90 ou 365 dias usando os botões no canto superior direito. O sistema usa cache de 5 minutos — KPIs podem levar até 5 min pra refletir mudanças.
  </div>
</section>

<!-- PÁGINA 3 — GRÁFICO + RANKING + CARDS -->
<section class="page">
  <h2>3. Gráfico de Remanejamentos por Dia</h2>
  <p>O gráfico de barras dourado mostra quantos remanejamentos aconteceram em cada dia do período selecionado. Barras altas = dias com mais movimento operacional.</p>
  <h3>Como usar:</h3>
  <ol class="steps">
    <li><strong>Identifique picos:</strong> Barras muito acima da média indicam dias críticos. Use pra investigar o que aconteceu (greve? navio extra? feriado?).</li>
    <li><strong>Drill-down:</strong> Clique em qualquer barra pra ver os remanejamentos daquele dia (modal abre com a lista detalhada).</li>
    <li><strong>Média diária:</strong> Aparece no canto superior direito do gráfico como referência.</li>
  </ol>

  <h2>4. Top Remanejados (ranking à direita)</h2>
  <p>Lista dos 10 TPAs com mais remanejamentos no período. Se um nome aparece no topo, vale conversar — pode ser sobrecarga ou padrão operacional.</p>

  <h2>5. Cards de Destaque (3 caixas escuras)</h2>
  <table>
    <thead>
      <tr><th>Card</th><th>Significado</th><th>Quando se preocupar</th></tr>
    </thead>
    <tbody>
      <tr><td>Função + remanejada</td><td>A função com mais remanejamentos</td><td>Concentração &gt; 50% do total</td></tr>
      <tr><td>Cais + problemático</td><td>O cais com mais remanejamentos</td><td>Sempre investigar (pode serlayout físico)</td></tr>
      <tr><td>Horário + crítico</td><td>O turno (DIURNO/NOTURNO) com mais movimento</td><td>Desbalanceamento &gt; 70%</td></tr>
    </tbody>
  </table>

  <div class="tip">
    💡 Se algum card mostrar "Sem dados", significa que aquele campo não foi preenchido nos remanejamentos. O sistema degrada graciosamente sem travar.
  </div>
</section>

<!-- PÁGINA 4 — INSIGHTS + EXPORT + SUPORTE -->
<section class="page">
  <h2>6. Insights Automáticos (caixas coloridas)</h2>
  <p>O BI gera 3 tipos de insight baseado em regras determinísticas:</p>
  <ul>
    <li><strong style="color: #d97706;">🟡 Alerta (amarelo):</strong> TPA remanejado 5+ vezes no período — investigar sobrecarga.</li>
    <li><strong style="color: #d97706;">🟡 Alerta (amarelo):</strong> Motivo concentrado &gt; 30% — considerar ação preventiva.</li>
    <li><strong style="color: #2563eb;">🔵 Info (azul):</strong> Pico de remanejamentos em 1 dia (&gt; 3× a média) — investigar causa.</li>
  </ul>

  <h2>7. Como exportar o relatório em PDF</h2>
  <ol class="steps">
    <li>No canto superior direito, clique no botão <strong>"📄 Exportar PDF"</strong> (cor dourada).</li>
    <li>O sistema gera um PDF de 1-2 páginas com capa + KPIs + gráfico + top + cards + insights.</li>
    <li>O download começa automaticamente. O arquivo vem com hash de integridade (proteção contra adulteração).</li>
    <li>Você pode enviar esse PDF pro OGMO, pra CCT, ou pro escritório de advocacia.</li>
  </ol>
  <p><strong>Tempo típico:</strong> &lt; 30 segundos. Se demorar mais, fale com o Paulo.</p>

  <h2>8. Suporte</h2>
  <table>
    <tbody>
      <tr><th>Problema</th><th>O que fazer</th></tr>
      <tr><td>Não consigo ver os KPIs</td><td>Verifique se você é DIRIGENTE. Fiscais não têm acesso (por design — BI é pra diretoria).</td></tr>
      <tr><td>Dados parecem errados</td><td>Compare com o sistema do OGMO. Se houver divergência, abra chamado com Paulo.</td></tr>
      <tr><td>PDF não baixa</td><td>Verifique bloqueador de pop-up. Ou peça pro Paulo rodar <code>curl /api/v1/bi/export-pdf</code> e enviar manualmente.</td></tr>
      <tr><td>Performance lenta</td><td>Cache é 5 min. Primeira carga pode levar 1-2s. Se &gt; 5s consistently, é bug — reportar.</td></tr>
    </tbody>
  </table>

  <h2>9. Glossário</h2>
  <p><strong>NACK:</strong> Notificação rejeitada pelo OGMO (motivo declarado). <strong>ACK:</strong> Aceita. <strong>Drill-down:</strong> Detalhe de um dia específico. <strong>BI:</strong> Business Intelligence (inteligência de negócio).</p>

  <footer>
    SINDESTIVA-PE · Lousa Digital · SINDESTIVA Bot · v1.0 · Setembro 2026
  </footer>
</section>

</body>
</html>"""


def main() -> int:
    HTML(string=HTML_DOC).write_pdf(str(OUTPUT))
    print(f"✓ Manual gerado: {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
