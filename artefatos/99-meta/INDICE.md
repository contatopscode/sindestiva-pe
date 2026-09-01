---
id: INDICE
versao: 1
status: ativo
data_atualizacao: 2026-09-01
---

# Índice de Artefatos · SINDESTIVA-PE · Lousa Digital

> Este índice lista **todos os artefatos do projeto** (não apenas o dicionário
> de dados) e aponta qual versão está **ativa** em cada categoria.
> Convenção: o índice aponta sempre para a versão mais recente; versões
> deprecated são preservadas em `historico/`.

---

## Estrutura atual

```
artefatos/
├── 01-briefing/                              ← Sprint 0 (Kickoff)
│   ├── 01-KICKOFF-PAUTA.md                   ✅ ativo
│   ├── 02-KICKOFF-ATA-TEMPLATE.md            ✅ ativo
│   ├── 03-BRIEFING-MANOEL.md                 ✅ ativo (Fiscal-piloto)
│   ├── 04-TERMO-LGPD-V1-DRAFT.md             ✅ draft (advogado revisar)
│   ├── 05-CARTA-OGMO-DRAFT.md                ✅ draft (Josias assina)
│   ├── 06-CHECKLIST-VISITA-SUAPE.md          ✅ ativo (K-4)
│   └── 07-CHECKLIST-NUMEROS-REAIS.md         ✅ ativo (K-3)
├── 05-dicionario-dados/
│   ├── DD-lousa-sindestiva-v1.md           ← ATIVO
│   └── DD-lousa-sindestiva-changelog.md    ← ATIVO
└── 99-meta/
    ├── INDICE.md                            ← este arquivo
    └── CONVENCOES.md                        ← ATIVO
```

> **Próximas pastas a criar** (à medida que o projeto avança):
> `02-prd/` (Sprint 1), `03-hu/` (Sprint 1+), `04-spec/` (Sprint 1+),
> `06-manuais/` (Sprint 9 — Go-Live).

---

## 05 · Dicionário de Dados (ativo)

| Artefato | Versão | Status | Path | Última atualização | Próxima revisão |
|---|---|---|---|---|---|
| **Dicionário de Dados** | **v1** | ✅ **ativo** | [`../05-dicionario-dados/DD-lousa-sindestiva-v1.md`](../05-dicionario-dados/DD-lousa-sindestiva-v1.md) | 2026-09-01 | pós-Sprint 1 (~22/09/2026) → v1.1 |
| **Changelog do DD** | **v1** | ✅ ativo | [`../05-dicionario-dados/DD-lousa-sindestiva-changelog.md`](../05-dicionario-dados/DD-lousa-sindestiva-changelog.md) | 2026-09-01 | a cada bump de versão |

> **Regra:** o `DD-lousa-sindestiva-v1.md` é a **fonte da verdade** do
> modelo conceitual. Qualquer divergência entre ele e o `AGENTS.md` ou
> `SINDESTIVA-PE-PLANO-IMPLEMENTACAO-2026-09-01.md` deve ser resolvida
> a favor do DD (mais específico) e gerar ADR.

---

## 99 · Meta (ativo)

| Artefato | Versão | Status | Path | Última atualização |
|---|---|---|---|---|
| **Convenções do DD** | **v1** | ✅ ativo | [`./CONVENCOES.md`](./CONVENCOES.md) | 2026-09-01 |
| **Índice** | **v1** | ✅ ativo | [`./INDICE.md`](./INDICE.md) | 2026-09-01 |

## 01 · Briefing do Kickoff (ativo)

| Artefato | Versão | Status | Path | Última atualização |
|---|---|---|---|---|
| **Pauta do Kickoff** | **v1** | ✅ ativo | [`../01-briefing/01-KICKOFF-PAUTA.md`](../01-briefing/01-KICKOFF-PAUTA.md) | 2026-09-01 |
| **Template de Ata** | **v1** | ✅ ativo | [`../01-briefing/02-KICKOFF-ATA-TEMPLATE.md`](../01-briefing/02-KICKOFF-ATA-TEMPLATE.md) | 2026-09-01 |
| **Briefing do Manoel (Fiscal-piloto)** | **v1** | ✅ ativo | [`../01-briefing/03-BRIEFING-MANOEL.md`](../01-briefing/03-BRIEFING-MANOEL.md) | 2026-09-01 |
| **Termo LGPD v1 (DRAFT)** | **v1** | ⚠️ draft | [`../01-briefing/04-TERMO-LGPD-V1-DRAFT.md`](../01-briefing/04-TERMO-LGPD-V1-DRAFT.md) | 2026-09-01 |
| **Carta OGMO (DRAFT)** | **v1** | ⚠️ draft | [`../01-briefing/05-CARTA-OGMO-DRAFT.md`](../01-briefing/05-CARTA-OGMO-DRAFT.md) | 2026-09-01 |
| **Checklist visita Suape (K-4)** | **v1** | ✅ ativo | [`../01-briefing/06-CHECKLIST-VISITA-SUAPE.md`](../01-briefing/06-CHECKLIST-VISITA-SUAPE.md) | 2026-09-01 |
| **Checklist números reais (K-3)** | **v1** | ✅ ativo | [`../01-briefing/07-CHECKLIST-NUMEROS-REAIS.md`](../01-briefing/07-CHECKLIST-NUMEROS-REAIS.md) | 2026-09-01 |

---

## Próximas versões planejadas (visão de roadmap)

| Versão | Quando | Escopo provável do DD | Vinculado a |
|---|---|---|---|
| **v1.1** | pós-Sprint 1 (~22/09/2026) | Ajustes pós-migration inicial (nomes de coluna, defaults, ENUMs faltantes) | Sprint 1 T1-02 + T1-03 |
| **v1.2** | pós-Sprint 5 (~16/11/2026) | Refinamento de `remanejamento_historico` × `audit_events`; otimização de índices após profiling | Sprint 5/6 + E2E testing |
| **v2.0** | pós-Go-Live (Fev/2027) | Camada analítica opcional (BI avançado), gatilhos para Fase 2, ICP-Brasil A1 (assinatura) | Fase 2 |
| **v2.1** | pós-Recife (Mar/2027) | Multi-porto com partição por `porto_id` (Fase 2) | Onboarding Recife |
| **v3.0** | Fase 3 (2027+) | **Multi-tenant (schema-per-OGMO)** — `lousa_<ogmo_slug>`, `ogmo_config` por tenant | B2B |

> **Decisão macro pendente (Paulo):** confirmar se o `lousa_main` deve ser
> renomeado para `lousa_suape` quando Recife entrar (Fase 2) ou se
> mantemos o nome atual e diferenciamos via coluna `porto_id`. Ver
> `DD-lousa-sindestiva-v1.md` §5 — Decisões abertas.

---

## Como usar este índice

1. **Antes de codar uma migration**: conferir aqui qual versão do DD está
   ativa; ler `CONVENCOES.md` para padrões de nomenclatura.
2. **Ao adicionar tabela/coluna**: seguir o workflow em `CONVENCOES.md` §6.
3. **Ao final de cada sprint**: revisar se algo do DD merece bump de versão.
4. **Em PR de migration**: referenciar a seção do DD que a motivou
   (ex: `DD-lousa-sindestiva-v1.md §3.14`).

---

*Mantido por SINDESTIVA Bot · última atualização 01/09/2026.*
