---
id: DD-lousa-sindestiva-changelog
versao: 1
status: ativo
ultima_atualizacao: 2026-09-01
manter_ate: indefinido
---

# Changelog · Dicionário de Dados · Lousa Digital

> Registro de versões do artefato `DD-lousa-sindestiva-v{N}.md`.
> Convenção: SemVer adaptado — **major** quebra de schema, **minor** novas tabelas, **patch** ajustes de coluna.

---

## v1 · 2026-09-01 · criação inicial

**Autor:** sindestiva-bot (agent SINDESTIVA Bot · Suporte Gerencial)
**Origem:** modelagem conceitual derivada de
- `SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md` (1090 linhas, 16 seções, fonte da verdade técnica)
- `SINDESTIVA-PE-PROTOTIPO.html` (6 telas: Lousa, Remanejamentos, OGMO, Auditoria, BI, PWA TPA)
- `SINDESTIVA-PE-CRONOGRAMA-45DIAS.md` (resumo executivo)
- `AGENTS.md` (padrão de stack e convenções do repo)

### Adicionado (26 tabelas)

| # | Tabela | Categoria | Justificativa |
|---|---|---|---|
| 1 | `users` | Auth | Base para NextAuth v5 — 3 roles (FISCAL/DIRIGENTE/TPA) |
| 2 | `roles` (enum) | Auth | RBAC — permissões por role |
| 3 | `tpas` | Pessoa | Trabalhador Portuário Avulso — 1:1 com users WHERE role='TPA' |
| 4 | `fiscais` | Pessoa | Fiscal do Sindicato — 1:1 com users WHERE role='FISCAL' |
| 5 | `dirigentes` | Pessoa | Presidente/diretoria — 1:1 com users WHERE role='DIRIGENTE' |
| 6 | `portos` | Dimensão | SUAPE, RECIFE (Sprint 1 seed) |
| 7 | `turnos` | Dimensão | DIURNO 08-16, NOTURNO 20-04 (Sprint 1 seed) |
| 8 | `funcoes` | Dimensão | 26 funções: Mando 6 + Terno 6 + Técnica 12 + Vigia 2 (Sprint 1 seed) |
| 9 | `fainas` | Dimensão | 10 fainas: Produção, Salário, Sacaria, Veículo, Diversos, Cadastro, Suplementar, Altura + 2 (Sprint 1 seed) |
| 10 | `navios` | Referência | Navios referenciados em BI ("MSC Aurora" etc.) — opcionalmente scraped |
| 11 | `cct_clausulas` | Jurídico | Base legal dos motivos de remanejamento (Sprint 5 T5-03) |
| 12 | `lousa_snapshots` | Lousa | Foto da lousa oficial por scrape (cron 60s) — Sprint 2 |
| 13 | `lousa_cells` | Lousa | 1.144 × N turnos/dia — quem está escalado onde (Sprint 2) |
| 14 | `remanejamentos` | Operação | Substituição de TPA com motivo + base legal (Sprint 5) |
| 15 | `remanejamento_historico` | Operação | Cada transição de status — desnormalizado para perf de query do `/remanejamentos` |
| 16 | `ogmo_notificacoes` | Integração | E-mail enviado ao OGMO com template + payload + status + hash (Sprint 5) |
| 17 | `ogmo_webhook_endpoints` | Integração | Endpoints cadastrados com HMAC-SHA256 — preparado (Fase 3 OGMO real) |
| 18 | `tpa_confirmacoes_presenca` | Operação | TPA confirma presença no navio — hash integridade (Sprint 3) |
| 19 | `termos_consentimento` | LGPD | Termo aceito pelo TPA — versão + IP + user_agent + timestamp (Sprint 1 K-5) |
| 20 | `audit_events` | Auditoria | Append-only com hash chain SHA-256 (Sprint 6 T6-12) |
| 21 | `hash_chain_checkpoint` | Auditoria | Verificador diário 03:00 (Sprint 6 T6-03) |
| 22 | `access_log` | LGPD | Quem viu dados de qual TPA, quando, IP (Sprint 6 T6-09) |
| 23 | `lgpd_solicitacoes` | LGPD | Art. 18 — solicitar exclusão, portabilidade, correção (Sprint 6 T6-07) |
| 24 | `lgpd_purge_log` | LGPD | Log de purga automática 24m — audit do audit (Sprint 6 T6-06) |
| 25 | `layout_fingerprints` | Scraper | Hash do HTML bruto do TPA/OGMO — alerta se divergir (Sprint 2 T2-03) |
| 26 | `feriados_nacionais` | Calendário | Antecipar envio se cair em fim de semana / feriado |

### Decisões macro vinculadas

- **ADR-001** (Scraping tolerante) → `lousa_snapshots` + `layout_fingerprints`
- **ADR-002** (Schema único no MVP) → `schema: lousa_main`
- **ADR-003** (Notificação OGMO por e-mail) → `ogmo_notificacoes` primário; `ogmo_webhook_endpoints` preparado
- **ADR-005** (Hash chain SHA-256) → `audit_events` + `hash_chain_checkpoint`
- **ADR-006** (Resend) → `ogmo_notificacoes.canais_envio` aceita 'EMAIL' / 'WEBHOOK'

### Riscos do plano vinculados ao modelo

- **R1 (OGMO/PE boicota)** — mitigado: `ogmo_notificacoes` registra **toda** tentativa de envio mesmo sem ACK. `ogmo_webhook_endpoints` fica vazio até OGMO responder.
- **R3 (MPT vê invasão)** — `audit_events` + `access_log` provam boa-fé; `termos_consentimento` é base legal do tratamento.
- **R4 (Fiscal não adota)** — `fiscais` rastreia uso (último login, último remanejamento); KPI de adoção em BI.

### Itens adiados (Fase 2/3 — não constam neste dicionário)

- ICP-Brasil A1 (Fase 2) — não cria coluna em `ogmo_notificacoes`; será adicionada em v2.
- SMS (Fase 2) — `ogmo_notificacoes.canais_envio` aceita 'SMS' como valor futuro, mas canal não é implementado.
- App nativo (Fase 2 se PWA limitar) — não impacta schema.
- API oficial OGMO (Fase 3) — `ogmo_webhook_endpoints` é o gancho.

---

## Próximas versões planejadas

| Versão | Quando | Escopo provável |
|---|---|---|
| **v1.1** | pós-Sprint 1 (~22/09/2026) | Ajustes pós-migration inicial (nomes de coluna, defaults) |
| **v1.2** | pós-Sprint 5 (~16/11/2026) | Refinamento de `remanejamento_historico` × `audit_events`; otimização de índices |
| **v2.0** | pós-Go-Live (Fev/2027) | Módulo BI avançado (camada analítica opcional), gatilhos Fase 2 |
| **v3.0** | Fase 3 (2027+) | Multi-tenant (schema-per-OGMO), BI preditivo, API oficial OGMO |

---

*Mantido por SINDESTIVA Bot · revisado por Paulo Siqueira (Sponsor técnico) a cada sprint review.*
