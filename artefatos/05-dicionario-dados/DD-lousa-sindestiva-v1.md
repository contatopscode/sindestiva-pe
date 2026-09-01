---
id: DD-lousa-sindestiva
versao: 1
status: draft
data_criacao: 2026-09-01
data_aprovacao: null
sprint_destino: S1 (fundação) — implementação das migrations iniciais
autor: sindestiva-bot (delega para coder implementar em S1 T1-02)
revisor: Paulo Siqueira (sponsor técnico + DPO)
stack: PostgreSQL 17 + SQLAlchemy 2.0 + Alembic
schema: lousa_main (MVP, ADR-002)
total_tabelas: 26
---

# Dicionário de Dados · Lousa Digital · v1

> **Status:** draft (aguardando revisão do Paulo no fim do Sprint 0 para virar
> referência da migration inicial do Sprint 1, atividade T1-02 do plano).
> **Próximo bump previsto:** v1.1 pós-migration inicial (~22/09/2026).

---

## 1. Visão geral

O banco do **Lousa Digital** guarda o estado operacional do SINDESTIVA-PE em
**3 eixos**: (1) **réplica da lousa oficial do OGMO/PE** (snapshots
periódicos + células atuais), (2) **remanejamentos formais** com notificação
ao OGMO (fila de e-mails + status SENT/PEND/ACK/NACK), e (3) **trilha de
auditoria imutável com hash chain SHA-256** para atender o MPT-PE. Tudo em
**schema único `lousa_main`** (ADR-002 — multi-tenant entra em Fase 3).

A separação entre `users` (auth — NextAuth v5) e `tpas`/`fiscais`/`dirigentes`
(perfil de negócio) reflete a decisão de manter 1 modelo de autenticação
único (3 roles) com 3 perfis de domínio. Soft delete + `purge_after` em
**toda tabela com dado pessoal** (LGPD, retenção 24m). Auditoria append-only
via `audit_events` com trigger Postgres que **bloqueia UPDATE/DELETE** (T6-12
do plano). **Risco #1 do plano (OGMO/PE boicota)** é mitigado pelo fato de
`ogmo_notificacoes` registrar **toda tentativa de envio** mesmo sem ACK — o
sistema funciona unilateralmente, OGMO é notificado mas não precisa
aprovar.

---

## 2. Entidades (resumo)

### 2.1 Diagrama ER textual (ASCII)

```
                                  ┌──────────────┐
                                  │  portos (6)  │  ← catálogo
                                  └──────┬───────┘
                                         │ 1
                                         │
                                  ┌──────▼───────┐    ┌──────────────┐
                                  │lousa_snapshots│ N  │  turnos (7)  │
                                  │   (12)        ├───►│              │
                                  └──────┬────────┘ N  └──────────────┘
                                         │ 1
                                         │
       ┌──────────┐                ┌─────▼─────┐                ┌──────────┐
       │ funcoes  │                │lousa_cells│                │ fainas   │
       │  (8)     │                │  (13)     │                │  (9)     │
       └────┬─────┘                └──┬────┬───┘                └────┬─────┘
            │                         │    │                        │
            │ N                       │ N  │ 1                      │ 1
            │                         │    │                        │
            │            ┌────────────┘    └────────────┐           │
            │            │                             │           │
            │       ┌────▼─────┐                 ┌─────▼────┐      │
            │       │  tpas    │ N               │ navios   │ (10) │
            │       │  (3)     │                 │  opcional│      │
            │       └────┬─────┘                 └──────────┘      │
            │            │ 1                                          │
            │            │                                           │
       ┌────▼────┐  ┌────▼─────────────┐                             │
       │ users   │  │remanejamentos    │                             │
       │  (1)    │  │  (14)            │                             │
       │  1—1 ◄──┼──┤  1               │                             │
       │   ↓     │  │  │               │                             │
       │   ↓ 1—1 │  │  │ N             │                             │
       │fiscais  │  │  ▼               │                             │
       │  (4)    │  │remanejamento_    │                             │
       │dirigentes│ │  historico (15)  │                             │
       │  (5)    │  └────┬─────────────┘                             │
       └────┬────┘       │                                           │
            │ 1          │ N                                         │
            │ N          ▼                                           │
            │     ┌──────────────┐                                   │
            │     │ogmo_notif.   │  ┌────────────────────┐            │
            │     │  (16)        │  │ogmo_webhook_endpts │            │
            │     │              │  │  (17) — preparado  │            │
            │     └──────────────┘  └────────────────────┘            │
            │                                                          │
            │ N                                                        │
            ▼                                                          │
       ┌──────────────┐  ┌──────────────────┐  ┌────────────────┐     │
       │termos_       │  │tpa_confirmacoes_ │  │lgpd_solicitac. │     │
       │consentimento │  │presenca (18)     │  │  (23)          │     │
       │  (19)        │  └──────────────────┘  └────────┬───────┘     │
       └──────────────┘                                  │             │
                                                         │ 1           │
                                                  ┌──────▼─────┐       │
                                                  │lgpd_purge_ │       │
                                                  │log (24)    │       │
                                                  └────────────┘       │
                                                                       │
       ┌──────────────┐  ┌──────────────────┐  ┌────────────────┐     │
       │audit_events  │  │hash_chain_       │  │access_log     │     │
       │  (20)        │  │checkpoint (21)   │  │  (22)         │     │
       │  append-only │  └──────────────────┘  └────────────────┘     │
       └──────────────┘                                                 │
                                                                       │
       ┌──────────────┐  ┌──────────────────┐  ┌────────────────┐     │
       │cct_clausulas │  │layout_           │  │feriados_       │     │
       │  (11)        │  │fingerprints (25) │  │nacionais (26)  │     │
       └──────────────┘  └──────────────────┘  └────────────────┘     │
```

### 2.2 Resumo por categoria

| # | Categoria | Tabelas | Justificativa |
|---|---|---|---|
| 1-2 | **Auth / RBAC** | `users`, `roles` (enum) | NextAuth v5 + 3 roles |
| 3-5 | **Pessoas** | `tpas`, `fiscais`, `dirigentes` | 3 perfis de domínio 1:1 com `users` |
| 6-11 | **Dimensão / catálogo** | `portos`, `turnos`, `funcoes`, `fainas`, `navios`, `cct_clausulas` | Seeds Sprint 1, imutáveis em prod |
| 12-13 | **Lousa espelhada** | `lousa_snapshots`, `lousa_cells` | Réplica do OGMO (Risco R2 mitigado) |
| 14-15 | **Remanejamento** | `remanejamentos`, `remanejamento_historico` | Operação central (M5 do plano) |
| 16-17 | **Integração OGMO** | `ogmo_notificacoes`, `ogmo_webhook_endpoints` | Risco R1 mitigado (unilateral) |
| 18 | **Confirmação TPA** | `tpa_confirmacoes_presenca` | Hash integridade (Sprint 3) |
| 19 | **LGPD base** | `termos_consentimento` | K-5 do plano, advogado valida |
| 20-22 | **Auditoria** | `audit_events`, `hash_chain_checkpoint`, `access_log` | Hash chain SHA-256 (ADR-005) |
| 23-24 | **LGPD Art. 18** | `lgpd_solicitacoes`, `lgpd_purge_log` | Retenção 24m, direito ao esquecimento |
| 25 | **Scraper** | `layout_fingerprints` | Alerta de mudança de layout (T2-03) |
| 26 | **Calendário** | `feriados_nacionais` | Antecipar envio se cair em fim de semana |

---

## 3. Tabelas

> Convenções aplicadas: ver `artefatos/99-meta/CONVENCOES.md`.
> Todas as tabelas com dado pessoal têm `deleted_at`, `purge_after` e
> `updated_at`. Tabelas marcadas **(audit)** têm trigger que bloqueia
> `UPDATE/DELETE`.

### 3.1 `users` — base de autenticação (NextAuth v5)

- **Propósito:** autenticação unificada de **fiscais, dirigentes e TPAs** via
  NextAuth v5 (credentials + OTP WhatsApp). Hospeda `password_hash`,
  `last_login`, flags de bloqueio.
- **Volume esperado:** ~2.020 linhas (10 fiscais + 10 dirigentes + ~2.000 TPAs)
- **LGPD:** sim — `email`, `telefone` (via `tpas`)
- **Retenção:** 24m após `deleted_at` (cascateia para perfis via FK RESTRICT)
- **Soft delete:** sim · campo `deleted_at`
- **Hash chain:** não (eventos de login vão para `audit_events`)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | Identificador universal |
| `email` | `citext` | ✓ | — | — | `uq_users_email` | Login primário; só p/ FISCAL/DIRIGENTE (TPA usa CPF+matrícula) |
| `telefone` | `text` | ✗ | NULL | — | `idx_users_telefone` | OTP WhatsApp do TPA; formato `+55DDXXXXXXXXX` |
| `password_hash` | `text` | ✗ | NULL | — | — | Argon2id; NULL até definir senha (TPA entra só com OTP) |
| `role` | `role_enum` | ✓ | — | — | `idx_users_role` | `FISCAL` \| `DIRIGENTE` \| `TPA` |
| `status` | `user_status_enum` | ✓ | `'PENDENTE_ACEITE'` | — | `idx_users_status` | `PENDENTE_ACEITE` → `ATIVO` → `BLOQUEADO` / `INATIVO` |
| `failed_login_count` | `integer` | ✓ | `0` | — | — | Rate limit local (5 errados → BLOQUEADO 15min) |
| `blocked_until` | `timestamptz` | ✗ | NULL | — | — | Janela de bloqueio (T8-01) |
| `last_login_at` | `timestamptz` | ✗ | NULL | — | — | Atualizado a cada login |
| `last_login_ip` | `inet` | ✗ | NULL | — | — | IPv4/IPv6 — audit |
| `last_login_user_agent` | `text` | ✗ | NULL | — | — | User-agent do browser/PWA |
| `accepted_terms_at` | `timestamptz` | ✗ | NULL | — | — | Primeiro aceite do termo LGPD |
| `accepted_terms_version` | `text` | ✗ | NULL | — | — | `v1.0`, `v1.1`... (imutável) |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | Auditoria implícita |
| `updated_at` | `timestamptz` | ✓ | `now()` | — | — | Trigger BEFORE UPDATE |
| `deleted_at` | `timestamptz` | ✗ | NULL | — | `idx_users_deleted_at` (parcial `WHERE deleted_at IS NULL`) | Soft delete |
| `purge_after` | `timestamptz` | ✓ | `now() + INTERVAL '24 months'` | — | `idx_users_purge_after` | LGPD — job diário `DELETE WHERE purge_after < now()` |

**Constraints:**
- `uq_users_email` — UNIQUE (email único por user)
- `ck_users_email_or_telefone` — CHECK (`email IS NOT NULL OR telefone IS NOT NULL`) — TPA pode entrar só com telefone
- `ck_users_password_for_non_tpa` — CHECK (`role <> 'TPA' OR password_hash IS NOT NULL`) ← **decisão aberta D1**

**Índices:** além dos óbvios: `idx_users_created_at` (crescimento)

**Observações:**
- Convenção `mixin.TimestampMixin` + `mixin.SoftDeleteMixin` (SQLAlchemy) gera
  `created_at`/`updated_at`/`deleted_at`/`purge_after` automaticamente.
- `role` é enum imutável após criação (não tem UPDATE nesse campo).
- Login events vão para `audit_events` (T6-12 do plano).

---

### 3.2 `roles` (enumerado, não tabela)

- **Propósito:** RBAC de 3 níveis + permissões granulares opcionais em
  `packages/shared/rbac.ts`. No MVP, `role` é campo enum em `users`. **Não há
  tabela `roles`** (decisão consciente — simplifica queries e alinhamento
  NextAuth). Permissões granulares por role:

| Role | Permissões MVP |
|---|---|
| `FISCAL` | Lousa (read), Remanejamentos (CRUD), OGMO (read), Auditoria (read), BI (read), próprio perfil (RWD) |
| `DIRIGENTE` | Tudo de FISCAL + BI (export PDF), `/admin/lgpd` (DPO), usuários (CRUD), métricas globais |
| `TPA` | Própria escala (read), confirmação de presença (CRUD próprio), perfil (RWD), solicitar exclusão LGPD |

**Matriz completa** em `packages/shared/rbac.ts` (Sprint 1 T1-05).

---

### 3.3 `tpas` — Trabalhador Portuário Avulso

- **Propósito:** perfil de negócio do TPA (1:1 com `users` onde
  `role='TPA'`). Cruzar matrículas OGMO com cadastro interno do Sindicato
  (T2-05).
- **Volume esperado:** ~2.000 linhas (Suape + Recife) — **D3** confirma com Manoel
- **LGPD:** sim — `cpf`, `nome_completo`, `telefone`, `data_nascimento`,
  `foto_url` (opcional, Fase 2)
- **Retenção:** 24m após desligamento (`deleted_at`)
- **Soft delete:** sim

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `user_id` | `uuid` | ✓ | — | `users(id)` | `uq_tpas_user_id` | 1:1 com `users` |
| `cpf` | `citext` | ✓ | — | — | `uq_tpas_cpf` | CHECK formato 11 dígitos |
| `nome_completo` | `text` | ✓ | — | — | `idx_tpas_nome_trgm` (pg_trgm) | Busca fuzzy no autocomplete |
| `matricula_ogmo` | `text` | ✓ | — | — | `uq_tpas_matricula_ogmo` | Matrícula oficial OGMO/PE (3 dígitos, ex: "012") |
| `data_nascimento` | `date` | ✗ | NULL | — | — | Opcional (não vem do OGMO) |
| `telefone` | `text` | ✓ | — | — | `idx_tpas_telefone` | OTP WhatsApp |
| `funcao_base_id` | `uuid` | ✓ | — | `funcoes(id)` | `idx_tpas_funcao_base` | Função que o TPA é habilitado a exercer |
| `categoria` | `text` | ✓ | — | — | `idx_tpas_categoria` | `MANDO` \| `TERNO` \| `TECNICA` \| `VIGIA` — denormalizado de `funcoes.categoria` p/ query rápida |
| `status_cadastro` | `tpa_status_enum` | ✓ | `'ATIVO'` | — | `idx_tpas_status_cadastro` | `ATIVO` \| `AFASTADO` \| `DESLIGADO` \| `SUSPENSO` |
| `data_admissao` | `date` | ✗ | NULL | — | — | Cadastro OGMO |
| `data_desligamento` | `date` | ✗ | NULL | — | `idx_tpas_data_desligamento` | Soft trigger para purge |
| `consentimento_at` | `timestamptz` | ✗ | NULL | — | — | Sincronizado com `termos_consentimento` (último aceite) |
| `consentimento_versao` | `text` | ✗ | NULL | — | — | Versão do termo aceito (imutável) |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `updated_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `deleted_at` | `timestamptz` | ✗ | NULL | — | parcial | |
| `purge_after` | `timestamptz` | ✓ | `now() + INTERVAL '24 months'` | — | `idx_tpas_purge_after` | |

**Constraints:**
- `uq_tpas_user_id`, `uq_tpas_cpf`, `uq_tpas_matricula_ogmo`
- `ck_tpas_cpf` — CHECK (`cpf ~ '^\d{11}$'`)
- `ck_tpas_matricula_ogmo` — CHECK (`length(matricula_ogmo) BETWEEN 1 AND 10`)

**Observações:**
- `categoria` denormalizado de `funcoes` para o BI poder agrupar sem JOIN
  (KPI "Taxa comparecimento por categoria" do Sprint 7).
- `matricula_ogmo` é a chave de cruzamento com a tabela oficial (Sprint 2
  T2-05 — matcher).
- Audit: todo `UPDATE` em `tpas` gera evento em `audit_events` (R3 do plano —
  MPT vê invasão; mitiga com rastreabilidade).

---

### 3.4 `fiscais` — Fiscal do Sindicato (Manoel Costa, perfil-piloto)

- **Propósito:** perfil de negócio do Fiscal (1:1 com `users` onde
  `role='FISCAL'`). Define porto-base e turno-base para autorização de
  remanejamentos.
- **Volume esperado:** ~10 linhas (Suape 7 + Recife 3)
- **LGPD:** sim — `nome_completo`, `telefone`, `cpf`
- **Retenção:** 5 anos após desligamento (audit fiscal/legal) — **D2**
- **Soft delete:** sim

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `user_id` | `uuid` | ✓ | — | `users(id)` | `uq_fiscais_user_id` | |
| `cpf` | `citext` | ✓ | — | — | `uq_fiscais_cpf` | |
| `nome_completo` | `text` | ✓ | — | — | `idx_fiscais_nome_trgm` | |
| `matricula_sindicato` | `text` | ✓ | — | — | `uq_fiscais_matricula_sindicato` | Matrícula interna (ex: "087-F") |
| `telefone` | `text` | ✓ | — | — | — | Contato operacional |
| `porto_id` | `uuid` | ✓ | — | `portos(id)` | `idx_fiscais_porto` | Porto base (SUAPE/RECIFE) |
| `turno_id` | `uuid` | ✓ | — | `turnos(id)` | — | Turno base (DIURNO/NOTURNO) |
| `status` | `fiscal_status_enum` | ✓ | `'ATIVO'` | — | `idx_fiscais_status` | `ATIVO` \| `AFASTADO` \| `DESLIGADO` |
| `data_inicio` | `date` | ✓ | — | — | — | |
| `data_fim` | `date` | ✗ | NULL | — | — | |
| `aprovador_id` | `uuid` | ✗ | NULL | `users(id)` (dirigente) | — | Quem cadastrou (audit) |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `updated_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `deleted_at` | `timestamptz` | ✗ | NULL | — | parcial | |
| `purge_after` | `timestamptz` | ✓ | `now() + INTERVAL '5 years'` | — | — | Retenção maior (audit) — **D2** |

**Observações:**
- `aprovador_id` é o Dirigente que cadastrou o Fiscal — necessário para
  auditoria (Sprint 6 T6-09 — quem liberou acesso a quem).
- Retenção 5a vs 24m dos TPAs: diferença justificada porque Fiscal tem
  responsabilidade fiscal/legal sobre os remanejamentos.

---

### 3.5 `dirigentes` — Presidente e Diretoria

- **Propósito:** perfil do Dirigente (Josias, diretores) — 1:1 com `users`
  onde `role='DIRIGENTE'`. Base para DPO dashboard (T6-08) e BI executivo.
- **Volume esperado:** ~5-10 linhas
- **LGPD:** sim (mesmo nível de Fiscal)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `user_id` | `uuid` | ✓ | — | `users(id)` | `uq_dirigentes_user_id` | |
| `cpf` | `citext` | ✓ | — | — | `uq_dirigentes_cpf` | |
| `nome_completo` | `text` | ✓ | — | — | — | |
| `cargo` | `text` | ✓ | — | — | — | "Presidente", "Vice-Presidente", "Diretor Financeiro", "Diretor de Comunicações" |
| `matricula_sindicato` | `text` | ✓ | — | — | `uq_dirigentes_matricula` | |
| `is_dpo` | `boolean` | ✓ | `false` | — | — | Apenas 1 user pode ter `true` (CHECK) — Paulo é o DPO |
| `data_inicio_mandato` | `date` | ✓ | — | — | — | |
| `data_fim_mandato` | `date` | ✗ | NULL | — | — | Pleito R15 do plano |
| ...timestamps e soft delete padrão |

**Constraints:**
- `ck_dirigentes_is_dpo_unico` — só pode haver 1 `is_dpo = true` ativo —
  verificação via trigger ou UPSERT controlado pela app

**Observações:**
- Pleito eleitoral (R15 do plano) → `data_fim_mandato` é populado e novo
  Dirigente é cadastrado; `users.old_director_id` mantém rastreabilidade.

---

### 3.6 `portos` — catálogo de portos

- **Propósito:** SUAPE, RECIFE. Catálogo imutável em produção (seed Sprint 1).
- **Volume esperado:** 2 linhas (fixo)
- **LGPD:** não
- **Retenção:** indefinida

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `codigo` | `text` | ✓ | — | — | `uq_portos_codigo` | `SUAPE`, `RECIFE` |
| `nome_completo` | `text` | ✓ | — | — | — | "Porto de Suape", "Porto do Recife" |
| `cnpj_ogmo` | `text` | ✗ | NULL | — | — | CNPJ do OGMO local |
| `url_tpa` | `text` | ✗ | NULL | — | — | URL do TPA Tecnologia (ex: `http://tpa.ogmosuape.com.br`) |
| `url_escalanet` | `text` | ✗ | NULL | — | — | URL do EscalaNet local |
| `is_active` | `boolean` | ✓ | `true` | — | — | |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `updated_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Observações:**
- Seed Sprint 1: 2 linhas (SUAPE + RECIFE).

---

### 3.7 `turnos` — catálogo de turnos

- **Propósito:** DIURNO 08-16, NOTURNO 20-04. Catálogo imutável.
- **Volume esperado:** 2 linhas (fixo)
- **LGPD:** não

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `codigo` | `text` | ✓ | — | — | `uq_turnos_codigo` | `DIURNO`, `NOTURNO` |
| `nome_exibicao` | `text` | ✓ | — | — | — | "08-16" |
| `hora_inicio` | `time` | ✓ | — | — | — | `08:00:00` |
| `hora_fim` | `time` | ✓ | — | — | — | `16:00:00` |
| `duracao_horas` | `numeric(4,2)` | ✓ | — | — | — | `8.00` |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Observações:**
- Seed Sprint 1: 2 linhas. **Decisão aberta D4** se vai ter turno
  intermediário (ex: 16-20 de sobreposição) — Manoel confirma.

---

### 3.8 `funcoes` — catálogo das 26 funções portuárias

- **Propósito:** as 26 funções da lousa oficial, distribuídas em 4
  categorias (Mando 6 + Terno 6 + Técnica 12 + Vigia 2). Catálogo imutável.
- **Volume esperado:** 26 linhas (fixo)
- **LGPD:** não

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `codigo` | `text` | ✓ | — | — | `uq_funcoes_codigo` | `GUINCHO_A`, `EMP_PP`, `VIGIA_PORTO`... |
| `nome_exibicao` | `text` | ✓ | — | — | `idx_funcoes_nome_trgm` | "Guincho A", "Emp. PP", "Vigia de Porto" |
| `categoria` | `text` | ✓ | — | — | `idx_funcoes_categoria` | `MANDO` \| `TERNO` \| `TECNICA` \| `VIGIA` |
| `ordem_lousa` | `integer` | ✓ | — | — | `uq_funcoes_ordem` | Posição na coluna da lousa (1-26) |
| `is_active` | `boolean` | ✓ | `true` | — | — | |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Constraints:**
- `uq_funcoes_codigo`, `uq_funcoes_ordem` (imutável)

**Seed Sprint 1** (referência do protótipo `SINDESTIVA-PE-PROTOTIPO.html`):
- **Mando (6):** C/M Geral, C/M Porão, C/M Bloco, C/M Rechego, C/M Cons., Supervisor
- **Terno (6):** Porão, Bloco MAX, Bloco, Rechego, Cons., Ship Loader
- **Técnica (12):** Sinaleiro, Guincho A, Guincho B, Emp. GP, Emp. PP, V. Pesado, V. Leve, Manobrista, Transp., Pá Mec., (+2 a definir com Manoel) — **D5**
- **Vigia (2):** Vigia Porto, Vigia Cais (a confirmar nomes)

**Observações:**
- A ordem das colunas na lousa é fixa (1-26). Mudanças exigem migration e
  atualização da UI (D5).

---

### 3.9 `fainas` — catálogo das 10 fainas

- **Propósito:** as 10 linhas da lousa (Produção, Salário, Sacaria, etc.).
  Catálogo imutável.
- **Volume esperado:** 10 linhas (fixo)
- **LGPD:** não

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `codigo` | `text` | ✓ | — | — | `uq_fainas_codigo` | `PRODUCAO`, `SALARIO`, `SACARIA`... |
| `nome_exibicao` | `text` | ✓ | — | — | — | "Produção", "Salário", "Sacaria"... |
| `cor_hex` | `text` | ✗ | NULL | — | — | Cor temática do CSS (`--fainas-producao`) |
| `ordem_lousa` | `integer` | ✓ | — | — | `uq_fainas_ordem` | Posição na linha da lousa (1-10) |
| `is_active` | `boolean` | ✓ | `true` | — | — | |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Seed Sprint 1** (referência do protótipo):
1. Produção
2. Salário
3. Sacaria
4. Veículo
5. Diversos
6. Cadastro
7. Suplementar
8. Altura
9. (a confirmar — protótipo mostra 10 mas só lista 8 por nome — **D5**)
10. (a confirmar)

---

### 3.10 `navios` — referência de navios atracados

- **Propósito:** navios referenciados em BI ("MSC Aurora" no protótipo) e em
  observações de remanejamento. **Não é scrape** — pode ser inserido
  manualmente pelo Fiscal ou importado em Sprint futuro.
- **Volume esperado:** ~100-500 navios/ano (Suape + Recife)
- **LGPD:** não

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `nome` | `text` | ✓ | — | — | `idx_navios_nome_trgm` | "MSC Aurora" |
| `imo` | `text` | ✗ | NULL | — | `uq_navios_imo` | IMO number (opcional, quando conhecido) |
| `bandeira` | `text` | ✗ | NULL | — | — | País de registro |
| `tipo_operacao` | `text` | ✗ | NULL | — | — | `RO_RO`, `CONTAINER`, `GRANEL`, `SACARIA` |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Observações:**
- Inserção via PWA ou Centro de Comando (autocomplete no modal de
  remanejamento).

---

### 3.11 `cct_clausulas` — base legal dos motivos

- **Propósito:** cláusulas da CCT 2024-2026 (e futuras) que fundamentam os
  motivos de remanejamento. Base legal exibida no modal e no PDF.
- **Volume esperado:** ~20-30 linhas
- **LGPD:** não (mas é documento jurídico — versioning importa)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `versao_cct` | `text` | ✓ | — | — | `idx_cct_versao` | `2024-2026`, `2026-2028` |
| `clausula` | `text` | ✓ | — | — | `uq_cct_versao_clausula` | `cl. 12ª, §3º` |
| `descricao` | `text` | ✓ | — | — | — | Texto integral da cláusula |
| `motivos_vinculados` | `text[]` | ✗ | NULL | — | `idx_cct_motivos_gin` | Array: `["ATESTADO_MEDICO", "LIBERACAO_ANTECIPADA"]` |
| `is_active` | `boolean` | ✓ | `true` | — | — | |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Observações:**
- Seed Sprint 1 é vazio; populado no Sprint 0 K-2 (Josias entrega CCT
  digitalizada) e Sprint 5 T5-03.
- Atualização de CCT é evento crítico: cria nova versão, marca anterior como
  `is_active = false`, **nunca apaga** (audit).

---

### 3.12 `lousa_snapshots` — foto da lousa OGMO num instante T

- **Propósito:** cada scrape do TPA/OGMO-PE (cron 60s durante operação) gera
  1 linha. É a **réplica fiel** da lousa oficial — Risco R1 do plano
  (OGMO boicota) é mitigado porque a integração é unilateral.
- **Volume esperado:** ~57.600 linhas/ano (16h operação × 60 scrape/h × 360
  dias = 3.456/dia; mas só 2 turnos → 720/dia por porto, ~518k/ano para os 2
  portos)
- **LGPD:** não (snapshot é dado funcional, sem PII)
- **Retenção:** **particionada por mês** (Postgres `PARTITION BY RANGE (created_at)`);
  após 12m os partitions vão pra tablespace frio (Sprint 8 T8-04)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `porto_id` | `uuid` | ✓ | — | `portos(id)` | `idx_lousa_snapshots_porto_created` | SUAPE ou RECIFE |
| `turno_id` | `uuid` | ✓ | — | `turnos(id)` | (composto) | |
| `fonte` | `text` | ✓ | — | — | — | `TPA_OGMO` \| `ESCALANET` \| `MANUAL_FISCAL` (fallback) |
| `url_origem` | `text` | ✗ | NULL | — | — | URL exata raspada (debug) |
| `html_hash_sha256` | `char(64)` | ✓ | — | — | `idx_lousa_snapshots_html_hash` | Hash do HTML bruto (R2 do plano — alerta de mudança) |
| `layout_fingerprint_id` | `uuid` | ✗ | NULL | `layout_fingerprints(id)` | — | Versão do layout usado no parse |
| `total_celulas` | `integer` | ✓ | — | — | — | 1.144 = 26 colunas × 11 fainas × 4 (portos × turnos) por snapshot — **D6** |
| `total_tpas_escalados` | `integer` | ✓ | — | — | — | Contagem de células não-vazias |
| `duracao_scrape_ms` | `integer` | ✓ | — | — | — | Latência scrape → DB (SLA < 5s) |
| `status` | `snapshot_status_enum` | ✓ | `'OK'` | — | `idx_lousa_snapshots_status` | `OK` \| `PARCIAL` \| `ERRO` \| `LAYOUT_MUDOU` |
| `erro_detalhes` | `text` | ✗ | NULL | — | — | Mensagem de erro se status ≠ OK |
| `scraped_at` | `timestamptz` | ✓ | `now()` | — | `idx_lousa_snapshots_scraped_at` | Quando o scraper rodou |
| `created_at` | `timestamptz` | ✓ | `now()` | — | (partição) | Inserção no banco |

**Constraints:**
- `fk_lousa_snapshots_porto` → `portos(id)` ON DELETE RESTRICT
- `fk_lousa_snapshots_turno` → `turnos(id)` ON DELETE RESTRICT

**Índices:**
- `idx_lousa_snapshots_porto_turno_scraped` (b-tree composto) — query do Centro de Comando
- `idx_lousa_snapshots_layout_fingerprint` — alerta de mudança

**Observações:**
- **PARTICIONAMENTO** por `RANGE (created_at)` mensal é mandatório no Sprint
  8 (volume 500k+/ano). Migration cria 12 partições iniciais + job mensal
  cria a próxima.
- `html_hash_sha256` é insumo de `layout_fingerprints` (T2-03 do plano).
- **Soft delete não se aplica** — snapshots são imutáveis e particionados;
  deleção é via `DROP PARTITION` (Sprint 8).

---

### 3.13 `lousa_cells` — cada célula da lousa (1.144 × N)

- **Propósito:** estado atual de cada célula da lousa: qual TPA está
  escalado em qual função/faina/turno/porto. **É o que o Centro de Comando
  renderiza em tempo real** (T4-02 do plano).
- **Volume esperado:** ~518k linhas/ano (mesma ordem de `lousa_snapshots`,
  mas normalizado — Sprint 2 D6)
- **LGPD:** **sim** — `tpa_id` (atravessa de `tpas` que tem CPF) — aplicar
  todas as proteções de `tpas`
- **Retenção:** 24m (audit de presença)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `snapshot_id` | `uuid` | ✓ | — | `lousa_snapshots(id)` ON DELETE CASCADE | `idx_lousa_cells_snapshot` | De qual snapshot veio |
| `porto_id` | `uuid` | ✓ | — | `portos(id)` | (composto) | |
| `turno_id` | `uuid` | ✓ | — | `turnos(id)` | (composto) | |
| `funcao_id` | `uuid` | ✓ | — | `funcoes(id)` | (composto) | Coluna 1-26 |
| `faina_id` | `uuid` | ✓ | — | `fainas(id)` | (composto) | Linha 1-10 |
| `cais` | `text` | ✗ | NULL | — | `idx_lousa_cells_cais` | Ex: "Cais 3" |
| `navio_id` | `uuid` | ✗ | NULL | `navios(id)` | `idx_lousa_cells_navio` | Navio atracado (Sprint 2+) |
| `tpa_id` | `uuid` | ✗ | NULL | `tpas(id)` | `idx_lousa_cells_tpa` | TPA escalado (NULL = célula vazia) |
| `status_celula` | `cell_status_enum` | ✓ | `'NORMAL'` | — | `idx_lousa_cells_status` | `NORMAL` \| `AUSENTE` \| `REMANEJADO` \| `CONFIRMADO` |
| `data_referencia` | `date` | ✓ | — | — | `idx_lousa_cells_data` | Data do turno (YYYY-MM-DD) — facilita BI |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Constraints:**
- `uq_lousa_cells_unique` — UNIQUE (`snapshot_id`, `funcao_id`, `faina_id`) — cada
  célula aparece no máximo 1x por snapshot
- FKs todas ON DELETE RESTRICT exceto `snapshot_id` (CASCADE porque snapshot
  é descartável)

**Índices críticos:**
- `idx_lousa_cells_porto_turno_data_funcao_faina` — query do Centro de
  Comando (1.144 cells)
- `idx_lousa_cells_tpa_data` — query "escala do TPA" no PWA
- `idx_lousa_cells_cais_data` — BI "Cais + problemático"

**Observações:**
- Células vazias (`tpa_id IS NULL`) também são gravadas (preservar histórico
  do scrape).
- `data_referencia` é desnormalizado para query rápida do BI sem precisar
  de JOIN com `lousa_snapshots`.
- Estratégia de retenção: **24m padrão LGPD** + partição mensal opcional
  (Sprint 8). Avaliar se mantemos histórico de **qualquer** célula ou só do
  último snapshot por turno — **D7** (impacto em performance de query do
  Centro de Comando).

---

### 3.14 `remanejamentos` — solicitação de substituição de TPA

- **Propósito:** o "coração" do sistema — Manoel clica na lousa, preenche o
  modal (motivo + base legal), e gera 1 remanejamento que vai virar e-mail
  pro OGMO. **SLA de 5 minutos** (T5-04) entre criação e notificação.
- **Volume esperado:** ~1.500-2.000/ano (média 5-6/dia conforme protótipo BI)
- **LGPD:** sim (TPA removido/inserido, fiscal, hash)
- **Retenção:** 5 anos (audit legal/trabalhista — Art. 7º LGPD inciso II +
  CLT art. 11)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `codigo_se` | `text` | ✓ | — | — | `uq_remanejamentos_codigo_se` | `SE-2026-0812-014` (Sistema + data + sequencial) — referência visível |
| `snapshot_origem_id` | `uuid` | ✗ | NULL | `lousa_snapshots(id)` | `idx_remanejamentos_snapshot` | Snapshot da lousa no momento do clique |
| `porto_id` | `uuid` | ✓ | — | `portos(id)` | (composto) | |
| `turno_id` | `uuid` | ✓ | — | `turnos(id)` | (composto) | |
| `data_referencia` | `date` | ✓ | — | — | `idx_remanejamentos_data` | Data do turno afetado |
| `tpa_out_id` | `uuid` | ✓ | — | `tpas(id)` | `idx_remanejamentos_tpa_out` | TPA sendo removido |
| `funcao_origem_id` | `uuid` | ✓ | — | `funcoes(id)` | — | Função que ele ocupava |
| `faina_origem_id` | `uuid` | ✓ | — | `fainas(id)` | — | |
| `cais_origem` | `text` | ✗ | NULL | — | — | |
| `tpa_in_id` | `uuid` | ✗ | NULL | `tpas(id)` | `idx_remanejamentos_tpa_in` | TPA a inserir (opcional — OGMO pode decidir) |
| `motivo` | `motivo_remanejamento_enum` | ✓ | — | — | `idx_remanejamentos_motivo` | `ATESTADO_MEDICO` \| `FALTA_INJUSTIFICADA` \| `REFORCO_TERNO` \| `TROCA_TURNO` \| `ATRASO_15MIN` \| `FALTA_EPI` \| `LIBERACAO_ANTECIPADA` \| `OUTRO` |
| `motivo_outro_texto` | `text` | ✗ | NULL | — | — | Preenchido se motivo = OUTRO |
| `base_legal_cct_id` | `uuid` | ✗ | NULL | `cct_clausulas(id)` | `idx_remanejamentos_cct` | FK para cláusula (T5-03) |
| `base_legal_texto_livre` | `text` | ✗ | NULL | — | — | Fallback se CCT não cadastrada |
| `observacoes` | `text` | ✗ | NULL | — | — | Notas do Fiscal |
| `anexo_url` | `text` | ✗ | NULL | — | — | URL do S3/object storage do atestado (mock no MVP) |
| `fiscal_id` | `uuid` | ✓ | — | `fiscais(id)` | `idx_remanejamentos_fiscal` | Quem criou |
| `status` | `status_remanejamento_enum` | ✓ | `'PENDENTE'` | — | `idx_remanejamentos_status` | `PENDENTE` → `APROVADO` → `NOTIFICADO_OGMO` → `ACK` \| `NACK` \| `CANCELADO` |
| `ack_at` | `timestamptz` | ✗ | NULL | — | — | Quando OGMO confirmou (se vier) |
| `ack_por` | `text` | ✗ | NULL | — | — | Quem confirmou (e-mail/nome) |
| `nack_motivo` | `text` | ✗ | NULL | — | — | Justificativa se OGMO recusar |
| `hash_evento` | `char(64)` | ✓ | — | — | `idx_remanejamentos_hash` | SHA-256 do JSON (ADR-005) |
| `hash_anterior_id` | `uuid` | ✗ | NULL | `remanejamentos(id)` | `idx_remanejamentos_hash_anterior` | Encadeamento |
| `created_at` | `timestamptz` | ✓ | `now()` | — | `idx_remanejamentos_created` | Quando Fiscal clicou "Executar" |
| `updated_at` | `timestamptz` | ✓ | `now()` | — | — | Trigger |
| `deleted_at` | `timestamptz` | ✗ | NULL | — | parcial | Soft delete (raro — só se erro) |
| `purge_after` | `timestamptz` | ✓ | `now() + INTERVAL '5 years'` | — | `idx_remanejamentos_purge_after` | Retenção 5a (legal) |

**Constraints:**
- `uq_remanejamentos_codigo_se` (gerado por trigger ou app no INSERT)
- `ck_remanejamentos_motivo_outro` — CHECK (`motivo <> 'OUTRO' OR motivo_outro_texto IS NOT NULL`)
- `ck_remanejamentos_base_legal` — CHECK (`base_legal_cct_id IS NOT NULL OR base_legal_texto_livre IS NOT NULL`)
- `ck_remanejamentos_ack_status` — CHECK (`status NOT IN ('ACK', 'NACK') OR ack_at IS NOT NULL`)

**Observações:**
- `codigo_se` é o ID visível no protótipo (`SE-2026-0812-014`); gerado por
  trigger BEFORE INSERT (`SE-` + `YYYYMMDD-` + sequencial diário).
- `status` enum tem **transições controladas pela app** (T5-10): `PENDENTE`
  → `APROVADO` (após validação interna) → `NOTIFICADO_OGMO` (após e-mail
  enviado) → `ACK`/`NACK` (futuro, via painel OGMO) ou `CANCELADO` (a
  qualquer momento, com motivo).
- Hash chain: `hash_evento = SHA256(json + hash_anterior.hash_evento)`. A
  coluna `hash_anterior_id` aponta para o remanejamento anterior na cadeia
  (não para `audit_events` — cadeia paralela por domínio).
- **Decisão aberta D8**: a cadeia de hash de `remanejamentos` deve ser
  encadeada com `audit_events` (cadeia única global) ou ser paralela?

---

### 3.15 `remanejamento_historico` — cada transição de status

- **Propósito:** append-only do ciclo de vida do remanejamento. Alimenta a
  tela `/remanejamentos` (T5-09) e o export PDF.
- **Volume esperado:** ~10.000-15.000 linhas/ano (~5-7 transições por
  remanejamento × 2.000 remanejamentos)
- **LGPD:** sim
- **Retenção:** 5 anos (igual `remanejamentos`)
- **Hash chain:** sim (mesma cadeia do `remanejamentos`)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `remanejamento_id` | `uuid` | ✓ | — | `remanejamentos(id)` | `idx_reman_hist_remanejamento_created` | |
| `status_anterior` | `status_remanejamento_enum` | ✗ | NULL | — | — | NULL na criação |
| `status_novo` | `status_remanejamento_enum` | ✓ | — | — | — | |
| `motivo_transicao` | `text` | ✗ | NULL | — | — | Por que mudou (ex: "OGMO respondeu por e-mail X") |
| `usuario_id` | `uuid` | ✗ | NULL | `users(id)` | — | Quem causou (Fiscal, OGMO via token, sistema) |
| `ip_origem` | `inet` | ✗ | NULL | — | — | |
| `user_agent` | `text` | ✗ | NULL | — | — | |
| `created_at` | `timestamptz` | ✓ | `now()` | — | (no índice composto) | |

**Constraints:** trigger BEFORE UPDATE/DELETE bloqueia (append-only)

**Observações:**
- Pode ser **substituído por `audit_events`** com `entity_type='remanejamento'`
  (D9) — decisão: manter como tabela dedicada para performance do
  `/remanejamentos` (query simples) e reconciliar com `audit_events` no job
  diário de verificação (T6-03).

---

### 3.16 `ogmo_notificacoes` — cada e-mail enviado ao OGMO

- **Propósito:** rastreabilidade de **toda** notificação ao OGMO (e-mail +
  webhook stub + painel). É a **prova documental** entregue ao OGMO/PE.
  Funciona **sem aprovação do OGMO** (R1 do plano).
- **Volume esperado:** ~2.000-3.000/ano (1 por remanejamento + retries)
- **LGPD:** sim (contém dados do TPA e do Fiscal)
- **Retenção:** 5 anos (audit)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `remanejamento_id` | `uuid` | ✓ | — | `remanejamentos(id)` | `idx_ogmo_notif_remanejamento` | 1 notificação por remanejamento (mais retries) |
| `canal` | `canal_notificacao_enum` | ✓ | — | — | `idx_ogmo_notif_canal` | `EMAIL` \| `WEBHOOK` \| `PAINEL_OGMO` (read-only) |
| `template_id` | `text` | ✓ | — | — | — | `remanejamento_v1`, `remanejamento_retry_v1` |
| `assunto` | `text` | ✗ | NULL | — | — | Assunto do e-mail |
| `payload_json` | `jsonb` | ✓ | — | — | `idx_ogmo_notif_payload_gin` | JSON completo enviado (T5-04) |
| `payload_hash_sha256` | `char(64)` | ✓ | — | — | `idx_ogmo_notif_hash` | Hash do payload (audit) |
| `destinatario_email` | `text` | ✗ | NULL | — | — | `escalacao@ogmosuape.com.br` (do `portos.url_tpa`) |
| `destinatario_webhook_id` | `uuid` | ✗ | NULL | `ogmo_webhook_endpoints(id)` | — | FK quando webhook |
| `provider_message_id` | `text` | ✗ | NULL | — | `idx_ogmo_notif_provider_id` | ID retornado pelo Resend (debug) |
| `status` | `status_notificacao_enum` | ✓ | `'PENDENTE'` | — | `idx_ogmo_notif_status` | `PENDENTE` → `ENVIADO` → `ENTREGUE` (provider confirmou) → `FALHOU` / `REJEITADO` |
| `tentativas` | `integer` | ✓ | `0` | — | — | Retry counter (T5-11: max 3) |
| `proxima_tentativa_em` | `timestamptz` | ✗ | NULL | — | `idx_ogmo_notif_proxima_tentativa` | Backoff 1m/5m/15m |
| `enviado_at` | `timestamptz` | ✗ | NULL | — | — | Provider aceitou |
| `entregue_at` | `timestamptz` | ✗ | NULL | — | — | Provider confirmou entrega (Resend webhook) |
| `falhou_at` | `timestamptz` | ✗ | NULL | — | — | |
| `erro_detalhes` | `text` | ✗ | NULL | — | — | Mensagem do provider |
| `pdf_anexo_url` | `text` | ✗ | NULL | — | — | URL do PDF no storage (Sprint 5 T5-06) |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `updated_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `purge_after` | `timestamptz` | ✓ | `now() + INTERVAL '5 years'` | — | — | |

**Constraints:**
- `ck_ogmo_notif_destinatario` — CHECK (canal = 'EMAIL' AND destinatario_email IS NOT NULL OR canal = 'WEBHOOK' AND destinatario_webhook_id IS NOT NULL OR canal = 'PAINEL_OGMO')

**Observações:**
- **Risco R1 (OGMO boicota)**: este tabela existe para provar que
  **tentamos notificar**. Mesmo sem ACK do OGMO, o sistema funciona
  unilateralmente.
- `payload_json` é `jsonb` (exceção à regra geral) — necessário porque o
  formato do webhook OGMO é livre e pode mudar (Fase 3).
- `payload_hash_sha256` é o hash visível no PDF (T5-06) — mesma cadeia SHA-256
  de `audit_events`.

---

### 3.17 `ogmo_webhook_endpoints` — endpoints cadastrados (preparado)

- **Propósito:** cadastro de endpoints do OGMO para notificação por
  webhook. **No MVP fica vazio** (OGMO/PE não respondeu a carta — R1 do
  plano). Estrutura já existe para quando OGMO topar (Fase 3).
- **Volume esperado:** 0-5 linhas
- **LGPD:** não (dado técnico)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `porto_id` | `uuid` | ✓ | — | `portos(id)` | — | |
| `url` | `text` | ✓ | — | — | — | `https://api.ogmo.com.br/v1/remanejamentos` |
| `secret_hmac` | `text` | ✓ | — | — | — | Segredo para HMAC-SHA256 (NUNCA retornar em GET) |
| `eventos_assinados` | `text[]` | ✓ | `'{remanejamento.criado, remanejamento.atualizado}'` | — | — | Eventos que disparam webhook |
| `is_active` | `boolean` | ✓ | `true` | — | — | |
| `ultimo_ping_at` | `timestamptz` | ✗ | NULL | — | — | Health check |
| `ultimo_ping_status` | `integer` | ✗ | NULL | — | — | HTTP status |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `updated_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Observações:**
- `secret_hmac` armazenado **criptografado** (pgcrypto ou KMS) — **D10**
  decisão de vault (KMS externo vs pgcrypto).
- Endpoint OGMO entra em contato via `/admin/ogmo/endpoints` (apenas Dirigente).

---

### 3.18 `tpa_confirmacoes_presenca` — TPA confirma presença no navio

- **Propósito:** o TPA, via PWA, confirma que **subiu no navio** (botão
  "Confirmar Presença" / "Não vou"). Gera evento que vai pro Fiscal e
  alimenta KPI de comparecimento (BI Sprint 7).
- **Volume esperado:** ~150.000-200.000/ano (2 turnos × 60% dos ~2.000 TPAs
  × 200 dias úteis)
- **LGPD:** sim (TPA + geolocalização opcional)
- **Retenção:** 24m (audit)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `tpa_id` | `uuid` | ✓ | — | `tpas(id)` | `idx_confirm_tpa_data` | |
| `lousa_cell_id` | `uuid` | ✗ | NULL | `lousa_cells(id)` | — | Célula da lousa confirmada (referência) |
| `data_referencia` | `date` | ✓ | — | — | (composto) | |
| `turno_id` | `uuid` | ✓ | — | `turnos(id)` | — | |
| `confirmou` | `boolean` | ✓ | — | — | — | TRUE = presente, FALSE = falta confirmada |
| `confirmado_at` | `timestamptz` | ✓ | `now()` | — | — | Quando clicou |
| `latitude` | `numeric(9,6)` | ✗ | NULL | — | — | Geo opcional (Sprint 3) |
| `longitude` | `numeric(9,6)` | ✗ | NULL | — | — | |
| `precisao_m` | `integer` | ✗ | NULL | — | — | Precisão do GPS |
| `dispositivo` | `text` | ✗ | NULL | — | — | "SM-A546E" (do FCM token) |
| `hash_integridade` | `char(64)` | ✓ | — | — | `idx_confirm_hash` | SHA-256(tpa_id + data + confirmou + timestamp) — anti-fraude |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `deleted_at` | `timestamptz` | ✗ | NULL | — | parcial | |
| `purge_after` | `timestamptz` | ✓ | `now() + INTERVAL '24 months'` | — | — | |

**Constraints:**
- `uq_confirm_tpa_data_turno` — UNIQUE (`tpa_id`, `data_referencia`, `turno_id`) — TPA confirma no máximo 1x por turno
- `ck_confirm_coordenadas` — CHECK (`latitude IS NULL OR latitude BETWEEN -90 AND 90`)

**Observações:**
- Geo é **opt-in** (Fase 2 — pedir permissão explicitamente no PWA).
- `hash_integridade` é anti-fraude: TPA não pode "confirmar presença" de
  outro TPA porque o hash inclui `tpa_id` autenticado.

---

### 3.19 `termos_consentimento` — termo LGPD aceito pelo TPA

- **Propósito:** registro imutável de cada aceite do termo de consentimento
  LGPD. **Base legal** do tratamento de dados pessoais. K-5 do plano
  (parecer do advogado).
- **Volume esperado:** ~3.000-5.000 linhas (cada TPA aceita 1x + versões
  futuras do termo)
- **LGPD:** sim (registro de consentimento é ele próprio dado pessoal)
- **Retenção:** **indefida** (ou enquanto o consentimento for vigente + 5a
  após revogação — **D11**)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `tpa_id` | `uuid` | ✓ | — | `tpas(id)` ON DELETE RESTRICT | `idx_termos_tpa_created` | |
| `versao_termo` | `text` | ✓ | — | — | `idx_termos_versao` | `v1.0`, `v1.1`... |
| `aceito` | `boolean` | ✓ | — | — | — | TRUE = aceitou, FALSE = **recusou** (registro de recusa é igualmente importante) |
| `aceito_em` | `timestamptz` | ✓ | `now()` | — | — | |
| `ip_origem` | `inet` | ✓ | — | — | — | Obrigatório (prova) |
| `user_agent` | `text` | ✓ | — | — | — | Obrigatório (prova) |
| `metodo` | `termo_metodo_enum` | ✓ | — | — | — | `PRIMEIRO_LOGIN` \| `RECONFIRMACAO` \| `ALTERACAO_TERMO` \| `REVOGACAO` |
| `termo_texto_hash` | `char(64)` | ✓ | — | — | — | SHA-256 do texto do termo aceito (prova de qual versão) |
| `termo_url_pdf` | `text` | ✗ | NULL | — | — | URL do PDF arquivado (S3) |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Constraints:** trigger BEFORE UPDATE/DELETE bloqueia (imutável)

**Observações:**
- A inserção é **automática** no fluxo de primeiro login (T1-10 do plano).
- Mesmo se o TPA **recusar** o termo, registramos (com `aceito = false`) —
  recusa é informação importante juridicamente.
- Texto do termo vive no S3 (versionado); banco guarda só o hash.

---

### 3.20 `audit_events` — log append-only com hash chain (ADR-005)

- **Propósito:** **a tabela mais crítica do sistema**. Captura **toda ação
  auditável** (login, criação de remanejamento, mudança de status, leitura
  de dado pessoal via `/admin/lgpd`, download de PDF, etc). Cada evento
  inclui o hash do evento anterior — qualquer adulteração quebra a cadeia
  e o verificador diário (T6-03) detecta.
- **Volume esperado:** ~50.000-100.000/ano (cada remanejamento gera ~3-5
  eventos; cada login = 1; cada leitura de PII = 1)
- **LGPD:** sim (logs de acesso a PII — T6-09)
- **Retenção:** **5 anos** (audit legal — Art. 7º LGPD + Portaria 1.224/18 MTb)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `sequencia` | `bigint` | ✓ | — | — | `uq_audit_events_sequencia` | Monotonic counter (gerado por sequence) |
| `entity_type` | `text` | ✓ | — | — | `idx_audit_entity` | `remanejamento` \| `lousa_cell` \| `tpa` \| `user` \| `ogmo_notificacao` \| `lgpd_solicitacao` \| `auth` |
| `entity_id` | `uuid` | ✗ | NULL | — | (composto) | ID da entidade afetada (NULL p/ eventos globais) |
| `event_type` | `text` | ✓ | — | — | `idx_audit_event_type` | `CREATE` \| `UPDATE` \| `DELETE` \| `READ` \| `STATUS_CHANGE` \| `LOGIN` \| `EXPORT` |
| `actor_user_id` | `uuid` | ✗ | NULL | `users(id)` | `idx_audit_actor` | Quem fez (NULL = sistema) |
| `actor_role` | `text` | ✗ | NULL | — | — | Denormalizado de `users.role` no momento (audit-safe) |
| `actor_ip` | `inet` | ✗ | NULL | — | — | |
| `actor_user_agent` | `text` | ✗ | NULL | — | — | |
| `payload_before` | `jsonb` | ✗ | NULL | — | `idx_audit_payload_gin` (parcial) | Snapshot antes (UPDATE/DELETE) |
| `payload_after` | `jsonb` | ✓ | — | — | `idx_audit_payload_gin` (parcial) | Estado novo ou evento |
| `metadata` | `jsonb` | ✗ | NULL | — | — | Dados extras (request_id, correlation_id, etc) |
| `hash_anterior` | `char(64)` | ✗ | NULL | — | — | Hash do evento anterior na cadeia global |
| `hash_evento` | `char(64)` | ✓ | — | — | `uq_audit_events_hash` (parcial único) | SHA-256 do JSON canonical + `hash_anterior` |
| `criado_em` | `timestamptz` | ✓ | `now()` | — | `idx_audit_criado_em` | |

**Constraints:**
- `tg_audit_events_block_update_delete` — trigger BEFORE UPDATE/DELETE
  levanta exception `AUDIT_IMMUTABLE`
- Sequence `audit_events_sequencia_seq` para `sequencia`
- `ck_audit_payload_consistent` — CHECK — `event_type <> 'UPDATE' OR payload_before IS NOT NULL`

**Índices críticos:**
- `idx_audit_entity_entity_id_created` (composto) — query por entidade
- `idx_audit_actor_created` — query "o que esse user fez"
- `idx_audit_event_type_created` — query "todos os CREATE de TPA"

**Observações:**
- **Cadeia única global** de hash chain — todos os eventos encadeiam,
  independente de `entity_type`. Isso garante que adulterar 1 evento quebra
  a cadeia inteira (mais seguro que cadeias paralelas).
- O verificador diário (`hash_chain_checkpoint`) recalcula do início e
  compara — alerta em `#audit-alerts` se quebrar (T6-03).
- `payload_after` é `jsonb` (exceção à regra geral) — necessário porque
  estrutura varia por `event_type`.

---

### 3.21 `hash_chain_checkpoint` — verificador diário 03:00

- **Propósito:** registrar o resultado de cada execução do job diário (03:00)
  que valida a integridade da hash chain. MPT/ANTAQ podem ver os últimos
  N checkpoints e provar que ninguém adulterou.
- **Volume esperado:** 365 linhas/ano
- **LGPD:** não (metadado técnico)
- **Retenção:** **indefinida** (prova de integridade histórica)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `executado_em` | `timestamptz` | ✓ | `now()` | — | `uq_hash_checkpoint_executado` | |
| `executado_por` | `text` | ✓ | — | — | — | `JOB_DIARIO` (sempre) |
| `total_eventos_verificados` | `bigint` | ✓ | — | — | — | |
| `primeiro_sequencia` | `bigint` | ✓ | — | — | — | Onde começou a varredura |
| `ultimo_sequencia` | `bigint` | ✓ | — | — | — | |
| `hash_calculado_final` | `char(64)` | ✓ | — | — | — | Hash do último evento recalculado |
| `hash_esperado_final` | `char(64)` | ✓ | — | — | — | Hash do último evento armazenado |
| `integro` | `boolean` | ✓ | — | — | `idx_hash_checkpoint_integro` | `hash_calculado = hash_esperado` |
| `primeiro_evento_com_falha` | `bigint` | ✗ | NULL | — | — | Se `integro = false`, sequência da primeira quebra |
| `duracao_ms` | `integer` | ✓ | — | — | — | Latência da verificação |
| `alerta_enviado` | `boolean` | ✓ | `false` | — | — | Canal `#audit-alerts` notificado? |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Observações:**
- Verificador (Sprint 6 T6-03) lê `audit_events` em chunks de 10k linhas e
  recalcula hash de cada uma comparando com `hash_evento` armazenado.
- Primeira execução após deploy pode demorar (full table scan);
  execuções subsequentes só validam os últimos 50k (janela de 24h).

---

### 3.22 `access_log` — log de acesso a dados pessoais (LGPD)

- **Propósito:** rastreabilidade de **toda leitura** de dado pessoal
  (Art. 37 LGPD — "registro das operações de tratamento"). T6-09 do plano.
- **Volume esperado:** ~30.000-50.000/ano (cada visualização de TPA no
  Centro de Comando = 1 evento; cada export = 1)
- **LGPD:** sim (é ele próprio um log de PII)
- **Retenção:** 5 anos (mesmo `audit_events`)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `user_id` | `uuid` | ✓ | — | `users(id)` | `idx_access_log_user_created` | Quem acessou |
| `recurso_tipo` | `text` | ✓ | — | — | `idx_access_log_recurso` | `tpa` \| `remanejamento` \| `lousa_cell` \| `audit_event` |
| `recurso_id` | `uuid` | ✓ | — | — | (composto) | ID do recurso acessado |
| `operacao` | `text` | ✓ | — | — | `idx_access_log_operacao` | `READ` \| `EXPORT_PDF` \| `EXPORT_CSV` |
| `contexto` | `text` | ✗ | NULL | — | — | "BI dashboard comparecimento" |
| `ip_origem` | `inet` | ✓ | — | — | — | |
| `user_agent` | `text` | ✓ | — | — | — | |
| `created_at` | `timestamptz` | ✓ | `now()` | — | (no índice composto) | |

**Observações:**
- Inserção é **automática** via middleware FastAPI (T6-09) — qualquer
  endpoint que retorne `tpa.cpf` ou similar gera 1 linha.
- Não tem hash chain próprio — eventos vão para `audit_events` (encadeados
  na cadeia global), e `access_log` é a **view materializada** para query
  rápida por TPA.

---

### 3.23 `lgpd_solicitacoes` — Art. 18 LGPD

- **Propósito:** workflow de solicitações do titular (TPA): exclusão,
  portabilidade, correção, confirmação de existência. T6-07 do plano.
- **Volume esperado:** ~20-50/ano (1-2/mês)
- **LGPD:** sim (a própria solicitação é PII)
- **Retenção:** **mínima 5a após conclusão** (Art. 16 LGPD — "registro do
  atendimento")

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `protocolo` | `text` | ✓ | — | — | `uq_lgpd_protocolo` | `LGPD-2026-0001` |
| `tpa_id` | `uuid` | ✓ | — | `tpas(id)` | `idx_lgpd_tpa` | Titular |
| `tipo` | `lgpd_tipo_enum` | ✓ | — | — | `idx_lgpd_tipo` | `EXCLUSAO` \| `PORTABILIDADE` \| `CORRECAO` \| `CONFIRMACAO_EXISTENCIA` \| `REVOGACAO_CONSENTIMENTO` |
| `descricao` | `text` | ✗ | NULL | — | — | Texto livre do titular |
| `status` | `lgpd_status_enum` | ✓ | `'RECEBIDA'` | — | `idx_lgpd_status` | `RECEBIDA` → `EM_ANALISE` → `DEFERIDA` / `INDEFERIDA` → `EXECUTADA` |
| `prazo_resposta` | `timestamptz` | ✓ | — | — | `idx_lgpd_prazo` | 15 dias (Art. 18 §5º) — preenchido por trigger |
| `recebida_em` | `timestamptz` | ✓ | `now()` | — | — | |
| `respondida_em` | `timestamptz` | ✗ | NULL | — | — | |
| `executada_em` | `timestamptz` | ✗ | NULL | — | — | Quando a ação foi concluída |
| `resposta_texto` | `text` | ✗ | NULL | — | — | |
| `documentos_anexos_url` | `text[]` | ✗ | NULL | — | — | Prova de identidade (CPF + documento) |
| `responsavel_user_id` | `uuid` | ✗ | NULL | `users(id)` | — | DPO (Paulo) que atendeu |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `updated_at` | `timestamptz` | ✓ | `now()` | — | — | |
| `purge_after` | `timestamptz` | ✓ | `now() + INTERVAL '5 years'` | — | — | Retenção mínima legal |

**Constraints:**
- `ck_lgpd_executada_status` — CHECK (`executada_em IS NULL OR status = 'EXECUTADA'`)

**Observações:**
- Trigger BEFORE INSERT calcula `prazo_resposta = recebida_em + 15 days`.
- **Exclusão** (DEFERIDA) dispara job que: 1) anonimiza `tpas` (cpf → hash,
  nome → "TPA EXCLUÍDO"), 2) preserva `audit_events` e `remanejamentos`
  com referência quebrada (`tpa_id` aponta para registro anonimizado), 3)
  registra em `lgpd_purge_log`.
- **Risco R10 do plano** (TPA processa) é mitigado por este workflow
  formal.

---

### 3.24 `lgpd_purge_log` — log da purga automática 24m

- **Propósito:** registrar **toda deleção automática** feita pelo job diário
  (T6-06) com base em `purge_after`. É "audit do audit" — prova que o job
  rodou, o que deletou, e por quê.
- **Volume esperado:** ~5.000-10.000 linhas/ano (milhares de linhas purged
  por execução do job)
- **LGPD:** sim (contém referência ao que foi deletado)
- **Retenção:** **10 anos** (audit do audit — mais que o audit original)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `executado_em` | `timestamptz` | ✓ | `now()` | — | `idx_purge_log_executado` | Quando o job rodou |
| `tabela_origem` | `text` | ✓ | — | — | `idx_purge_log_tabela` | Tabela que foi purgada |
| `registros_deletados` | `integer` | ✓ | — | — | — | Quantos |
| `criterio` | `text` | ✓ | — | — | — | `"purge_after < now()"` |
| `registros_ids_antes_delete` | `jsonb` | ✓ | — | — | `idx_purge_log_ids_gin` | Array dos IDs deletados (prova) |
| `hash_lote_sha256` | `char(64)` | ✓ | — | — | — | Hash do batch (audit) |
| `job_id` | `text` | ✓ | — | — | — | Identificador do job run (Kubernetes/Cron) |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Constraints:** trigger BEFORE UPDATE/DELETE bloqueia (imutável)

**Observações:**
- Job (T6-06) executa diariamente, lê `purge_after` de **todas** as tabelas
  com esse campo, e deleta em batch.
- Preserva referência histórica (ID + tabela) mesmo após deleção da linha
  original.

---

### 3.25 `layout_fingerprints` — fingerprint do layout OGMO

- **Propósito:** detectar mudança de layout do TPA/OGMO-PE (R2 do plano).
  Cada scrape calcula hash da estrutura (não do HTML bruto) e compara com
  último conhecido.
- **Volume esperado:** ~50-200 linhas (1 por mudança detectada)
- **LGPD:** não
- **Retenção:** 5 anos (audit técnico)

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `porto_id` | `uuid` | ✓ | — | `portos(id)` | — | |
| `versao` | `integer` | ✓ | — | — | `uq_fingerprints_porto_versao` | Incremental por porto |
| `html_hash_sha256` | `char(64)` | ✓ | — | — | — | Hash do HTML bruto (correlaciona com `lousa_snapshots.html_hash_sha256`) |
| `seletores_parser` | `jsonb` | ✓ | — | — | `idx_fingerprints_seletores_gin` | Seletores CSS/XPath que funcionaram (parser tolerante) |
| `fingerprint_estrutura` | `jsonb` | ✓ | — | — | `idx_fingerprints_estrutura_gin` | Resumo estrutural (nº de linhas, colunas, classes CSS) |
| `total_snapshots_validados` | `bigint` | ✓ | `0` | — | — | Quantos snapshots usaram esse fingerprint |
| `is_current` | `boolean` | ✓ | `true` | — | `uq_fingerprints_porto_current` (parcial) | Apenas 1 `is_current = true` por porto |
| `detectado_em` | `timestamptz` | ✓ | `now()` | — | — | Quando esse fingerprint apareceu |
| `substituido_em` | `timestamptz` | ✗ | NULL | — | — | Quando deixou de ser o atual |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Constraints:**
- `uq_fingerprints_porto_versao` — UNIQUE
- `uq_fingerprints_porto_current` — UNIQUE parcial (`WHERE is_current = true`)

**Observações:**
- Job (T2-03) detecta: `html_hash` mudou vs. último conhecido → cria novo
  fingerprint, marca anterior `is_current = false`, dispara alerta em
  `#scraper-alerts` (WhatsApp + e-mail) em < 5 min.
- `seletores_parser` é insumo para o parser se adaptar automaticamente
  (regex fallback) — **D12** se vamos de heurística ou ML simples.

---

### 3.26 `feriados_nacionais` — calendário (auxiliar)

- **Propósito:** antecipar envio de e-mail ao OGMO se o remanejamento
  cair em véspera de feriado / fim de semana (decisão operacional).
- **Volume esperado:** ~15-20 linhas (atualizado anualmente)
- **LGPD:** não
- **Retenção:** 10 anos

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| `id` | `uuid` | ✓ | `gen_random_uuid()` | — | PK | |
| `data` | `date` | ✓ | — | — | `uq_feriados_data` | |
| `nome` | `text` | ✓ | — | — | — | "Proclamação da República" |
| `tipo` | `text` | ✓ | — | — | `idx_feriados_tipo` | `NACIONAL` \| `ESTADUAL_PE` \| `MUNICIPAL_SUAPE` \| `MUNICIPAL_RECIFE` |
| `is_recorrente` | `boolean` | ✓ | `false` | — | — | Se true, mesma data todo ano (Tratado/Tiradentes) |
| `created_at` | `timestamptz` | ✓ | `now()` | — | — | |

**Observações:**
- Seed inicial via API ou SQL; manutenção anual.
- **Fora do MVP** se for priorizar — manter só a tabela reservada e
  popular no Sprint 7/8.

---

## 4. Relacionamentos

### 4.1 Cardinalidades principais

| De | Para | Cardinalidade | ON DELETE | Justificativa |
|---|---|---|---|---|
| `users` | `tpas` | 1:1 | RESTRICT | 1 user TPA = 1 perfil TPA |
| `users` | `fiscais` | 1:1 | RESTRICT | |
| `users` | `dirigentes` | 1:1 | RESTRICT | |
| `portos` | `lousa_snapshots` | 1:N | RESTRICT | Snapshot sempre tem porto |
| `lousa_snapshots` | `lousa_cells` | 1:N | **CASCADE** | Snapshot é descartável |
| `tpas` | `lousa_cells` | 1:N | RESTRICT | |
| `funcoes` | `lousa_cells` | 1:N | RESTRICT | |
| `fainas` | `lousa_cells` | 1:N | RESTRICT | |
| `navios` | `lousa_cells` | 1:N | SET NULL | Navio some → célula fica sem navio |
| `remanejamentos` | `remanejamento_historico` | 1:N | RESTRICT | Histórico é parte do remanejamento |
| `remanejamentos` | `ogmo_notificacoes` | 1:N | RESTRICT | 1 remanejamento → várias tentativas |
| `ogmo_webhook_endpoints` | `ogmo_notificacoes` | 1:N | SET NULL | |
| `tpas` | `tpa_confirmacoes_presenca` | 1:N | RESTRICT | |
| `tpas` | `termos_consentimento` | 1:N | RESTRICT | |
| `tpas` | `lgpd_solicitacoes` | 1:N | RESTRICT | |
| `cct_clausulas` | `remanejamentos` | 1:N | RESTRICT | |
| `users` | `audit_events` | 1:N (actor) | RESTRICT | `audit_events` é imutável |
| `users` | `access_log` | 1:N | RESTRICT | |
| `users` | `remanejamentos` (fiscal) | 1:N | RESTRICT | |
| `portos` | `layout_fingerprints` | 1:N | RESTRICT | |

### 4.2 Diagrama textual de alto nível

```
users ──┬── tpas ─────┬── lousa_cells ◄──── lousa_snapshots ◄── portos
        ├── fiscais ──┤                                            ├── turnos
        └── dirigentes┤                                            ├── funcoes
                     │                                              ├── fainas
                     ├── remanejamentos ──► remanejamento_historico  └── navios
                     │      │
                     │      ├── cct_clausulas (base legal)
                     │      └── ogmo_notificacoes ──► ogmo_webhook_endpoints
                     │
                     ├── tpa_confirmacoes_presenca
                     ├── termos_consentimento
                     ├── lgpd_solicitacoes ──► lgpd_purge_log
                     │
                     ├── audit_events ◄── (todas as tabelas alimentam)
                     ├── access_log
                     └── hash_chain_checkpoint (verifica audit_events)
```

---

## 5. Decisões abertas (precisam do Paulo antes da implementação)

> Estas decisões **bloqueiam ou afetam a migration inicial do Sprint 1**.
> Recomendo resolver no fim do Sprint 0 (K-1 a K-7 do plano) para entrar
> no Sprint 1 com schema travado.

### D1 · TPA pode ter `password_hash` ou só OTP?

**Contexto:** a constraint `ck_users_password_for_non_tpa` foi incluída mas é
arbitrária. TPA pode definir senha no PWA pra entrar mais rápido (sem
esperar OTP) ou só OTP é mais seguro?
**Opções:**
- (a) TPA **só OTP** (mais seguro, UX mais lenta)
- (b) TPA pode definir senha **opcional** (mais rápido, menos seguro)
**Recomendação SINDESTIVA Bot:** (a) — LGPD prefere menos vetores.
**Esforço de migração:** zero (só remover CHECK).

### D2 · Retenção de Fiscais/Dirigentes é 5a ou 24m?

**Contexto:** tabelas `fiscais`/`dirigentes` têm `purge_after = now() + 5 years`
porque têm responsabilidade legal. Mas se o Fiscal virou inativo, 24m
bastaria?
**Recomendação SINDESTIVA Bot:** manter 5a para fiscais (audit fiscal/legal),
24m para dirigentes (igual TPA).
**Esforço de migração:** zero.

### D3 · Volume real de TPAs (Suape + Recife)

**Contexto:** o protótipo fala em "1.142 TPAs" (26×11×4), mas isso é o
número de **células**, não de **pessoas**. Manoel Costa precisa confirmar
na visita a Suape (K-3): quantos TPAs ativos?
**Recomendação SINDESTIVA Bot:** assumir 2.000 (alinhado com a persona do
plano).
**Esforço de migração:** zero — é só ajuste de expectativa.

### D4 · Turno intermediário (16-20, 04-08)?

**Contexto:** o protótipo mostra 2 turnos (08-16, 20-04). Mas pode haver
sobreposição (turno 16-20 de交接). Manoel confirma.
**Recomendação SINDESTIVA Bot:** começar com 2 turnos; adicionar 3º se
Manoel pedir.
**Esforço de migração:** pequeno (mais 1 linha em `turnos`).

### D5 · Lista oficial das 10 fainas e 26 funções

**Contexto:** protótipo lista 8 fainas por nome mas diz "10"; funções
Técnica lista 10 (Sinaleiro, Guincho A, Guincho B, Emp. GP, Emp. PP, V.
Pesado, V. Leve, Manobrista, Transp., Pá Mec.) — precisam de 12. Falta
confirmar com Manoel.
**Recomendação SINDESTIVA Bot:** Manoel preenche planilha em K-3; seed
Sprint 1 depende.
**Esforço de migração:** pequeno (atualizar `funcoes`/`fainas` seed).

### D6 · Normalização de `lousa_cells` (1.144 vs 518k/ano)

**Contexto:** 1 snapshot = 1.144 células; 720 snapshots/dia × 360 dias =
259.200 células/dia = **93M/ano**. Muito volume. Alternativas:
- (a) Gravar **todas** (histórico completo, query simples)
- (b) Gravar **só último snapshot por turno** + histórico agregado diário
  (~720/dia + 1 agregado = performance ganha, BI mais pobre)
- (c) Particionar + arquivar após 6m
**Recomendação SINDESTIVA Bot:** (a) com particionamento mensal — mais
simples, e Postgres aguenta com índice certo.
**Esforço de migração:** médio (partition + jobs de manutenção).

### D7 · Soft delete em `lousa_cells`?

**Contexto:** tabela tem volume alto; `deleted_at` adiciona 1 coluna +
índice parcial. Soft delete **faz sentido** aqui se LGPD exige rastreio de
remoção.
**Recomendação SINDESTIVA Bot:** **não** usar soft delete em `lousa_cells` —
a tabela é particionada e a retenção é via partição, não por linha.
**Esforço de migração:** zero (só não criar).

### D8 · Hash chain de `remanejamentos` é encadeada com `audit_events` ou paralela?

**Contexto:** `remanejamentos.hash_evento` referencia o remanejamento
anterior; `audit_events.hash_evento` referencia o evento de auditoria
anterior. Podem ser:
- (a) **Cadeia única global** (tudo encadeia — `audit_events` é a fonte)
- (b) **Cadeias paralelas** (cada tabela tem sua própria)
**Recomendação SINDESTIVA Bot:** (a) — `remanejamento_historico` e
`remanejamentos` geram eventos em `audit_events`, que mantém a cadeia
única. O hash em `remanejamentos.hash_evento` vira redundante e pode ser
removido.
**Esforço de migração:** pequeno.

### D9 · `remanejamento_historico` × `audit_events` — manter 2 ou unificar?

**Contexto:** ambas tabelas registram transições de status do remanejamento.
Manter 2 = redundância + risco de divergência. Unificar = queries mais
lentas no `/remanejamentos`.
**Recomendação SINDESTIVA Bot:** unificar em `audit_events` (com
`entity_type='remanejamento'`) e criar **view** `vw_remanejamento_historico`
para o `/remanejamentos`. Reduz risco de divergência.
**Esforço de migração:** médio (view + remoção da tabela em migration
separada).

### D10 · `ogmo_webhook_endpoints.secret_hmac` — pgcrypto ou KMS externo?

**Contexto:** o segredo HMAC precisa ser armazenado criptografado. Opções:
- (a) **pgcrypto** (`pgp_sym_encrypt`) — simples, chave no env
- (b) **Vault externo** (HashiCorp Vault, AWS Secrets Manager) — mais
  seguro, mais complexo
**Recomendação SINDESTIVA Bot:** (a) no MVP (Fase 3 quando webhook entrar
de verdade, migrar para (b)).
**Esforço de migração:** pequeno.

### D11 · Retenção de `termos_consentimento` — indefinida ou 5a pós-revogação?

**Contexto:** ANPD recomenda manter registro de consentimento enquanto o
tratamento existir + 5a após o fim. Mas há discussão se a recusa
(`aceito = false`) também precisa ser mantida indefinidamente.
**Recomendação SINDESTIVA Bot:** manter **enquanto houver relação + 5a
após exclusão**. Implementar via job que deleta `termos_consentimento` de
TPAs com `tpas.deleted_at < now() - 5 years`.
**Esforço de migração:** pequeno.

### D12 · Parser tolerante — heurística ou ML?

**Contexto:** `layout_fingerprints.seletores_parser` precisa decidir qual
seletor usar quando o layout do TPA muda. Heurística (regex + fallback)
funciona para 90% dos casos; ML simples (regressão) detecta padrões.
**Recomendação SINDESTIVA Bot:** **heurística** no MVP (mesmo padrão
Sinapse). ML em Fase 2.
**Esforço de migração:** zero.

### D13 · Onde mora o "matcher" de TPAs (matrícula × cadastro)?

**Contexto:** Sprint 2 T2-05 diz "matcher de TPAs". Esse matcher pode ser:
- (a) Coluna `tpas.matricula_sindicato` (interna) + matcher em código
- (b) Tabela de junção `tpa_match_sindicato` (N:N para casos de matrícula
  alterada)
**Recomendação SINDESTIVA Bot:** (a) para o MVP — 1 matrícula OGMO = 1 TPA.
**Esforço de migração:** zero.

---

## 6. Rastreabilidade (HUs do plano → tabelas)

> Mapeamento das **86 HUs do plano de implementação** (Sprints 0-10) para
> as tabelas que as sustentam. Útil para priorização de migration e para o
> coder saber qual tabela implementar antes.

### 6.1 Sprint 0 — Kickoff (sem dependência de schema)

| HU | Atividade | Tabelas |
|---|---|---|
| K-2 | CCT obtida | (futuro: `cct_clausulas` seed) |
| K-3 | Números reais | (alimenta expectativa de volume) |
| K-5 | Termo LGPD | (futuro: `termos_consentimento` seed) |

### 6.2 Sprint 1 — Fundação (T1-02 modelagem)

| HU | Atividade | Tabelas |
|---|---|---|
| T1-02 | **Modelagem do banco** | TODAS as 26 tabelas deste DD |
| T1-03 | Seed | `portos`, `turnos`, `funcoes`, `fainas`, `users` (3 seeds), `tpas`, `fiscais`, `dirigentes`, `cct_clausulas` (vazio), `feriados_nacionais` |
| T1-04 | Auth | `users`, `tpas`, `fiscais`, `dirigentes` |
| T1-05 | RBAC | `users.role` (enum), `roles` (matriz em código) |
| T1-10 | LGPD middleware | `termos_consentimento` |

### 6.3 Sprint 2 — Scraping

| HU | Tabelas |
|---|---|
| T2-01, T2-02, T2-04 | `lousa_snapshots`, `lousa_cells`, `portos`, `turnos`, `funcoes`, `fainas`, `navios` |
| T2-03 | `layout_fingerprints` |
| T2-05 | `tpas.matricula_ogmo` + matcher (D13) |
| T2-06, T2-07 | API endpoints (read-only em `lousa_snapshots`/`lousa_cells`) |

### 6.4 Sprint 3 — PWA TPA

| HU | Tabelas |
|---|---|
| T3-02 | `users`, `tpas` (login CPF+matrícula+OTP) |
| T3-03 a T3-05 | `lousa_cells` (read) |
| T3-06 | `tpas`, `users` (perfil + edição) |
| T3-07 | `tpa_confirmacoes_presenca` |
| T3-13 | `termos_consentimento`, `lgpd_solicitacoes` (formulário) |

### 6.5 Sprint 4 — Centro de Comando (Lousa)

| HU | Tabelas |
|---|---|
| T4-01 a T4-04 | `lousa_snapshots`, `lousa_cells` (read) |
| T4-05 | WebSocket push de `lousa_snapshots` novos |
| T4-06 | `remanejamentos`, `ogmo_notificacoes` (fila) |
| T4-08 | `remanejamentos` (modal de criação) |

### 6.6 Sprint 5 — Remanejamento + Notificação OGMO

| HU | Tabelas |
|---|---|
| T5-01 | `remanejamentos` (POST) |
| T5-02, T5-03 | `remanejamentos`, `cct_clausulas` |
| T5-04 | `remanejamentos.hash_evento`, `audit_events` (criação) |
| T5-05, T5-06 | `ogmo_notificacoes` (e-mail + PDF) |
| T5-07 | `ogmo_webhook_endpoints`, `ogmo_notificacoes` (canal webhook) |
| T5-08 | `remanejamentos`, `ogmo_notificacoes` (read-only) |
| T5-09 | `remanejamentos`, `remanejamento_historico` (consulta) |
| T5-10 | `remanejamentos.status` (transições) |
| T5-11 | `ogmo_notificacoes.tentativas`, `proxima_tentativa_em` |

### 6.7 Sprint 6 — Auditoria + LGPD

| HU | Tabelas |
|---|---|
| T6-01 | `audit_events` (GET) |
| T6-02 | `audit_events`, `hash_chain_checkpoint` (UI) |
| T6-03 | `hash_chain_checkpoint` (job) |
| T6-04, T6-05 | `audit_events` (export) |
| T6-06 | `lgpd_purge_log` (job) + `purge_after` em todas as tabelas |
| T6-07 | `lgpd_solicitacoes` (workflow TPA) |
| T6-08 | `lgpd_solicitacoes`, `termos_consentimento` (DPO) |
| T6-09 | `access_log` |
| T6-12 | trigger `tg_audit_events_block_update_delete` em `audit_events` |

### 6.8 Sprint 7 — BI

| HU | Tabelas |
|---|---|
| T7-01 a T7-07 | agregações sobre `remanejamentos`, `tpa_confirmacoes_presenca`, `ogmo_notificacoes`, `lousa_cells` |
| T7-08 | cache Redis (fora do schema) |

### 6.9 Sprint 8 — Hardening

| HU | Tabelas |
|---|---|
| T8-01 | `users.failed_login_count`, `users.blocked_until` (rate limit) |
| T8-04 | Backup DB (todas) |
| T8-06 | Índices adicionais em `lousa_snapshots`, `remanejamentos`, `audit_events` |

### 6.10 Sprint 9 — Homologação (sem novas tabelas)

### 6.11 Sprint 10 — Go-Live (sem novas tabelas)

---

## 7. Resumo executivo

| Métrica | Valor |
|---|---|
| **Total de tabelas** | 26 |
| **Tabelas com dado pessoal (LGPD)** | 13 (`users`, `tpas`, `fiscais`, `dirigentes`, `remanejamentos`, `remanejamento_historico`, `ogmo_notificacoes`, `tpa_confirmacoes_presenca`, `termos_consentimento`, `audit_events`, `access_log`, `lgpd_solicitacoes`, `lgpd_purge_log`) |
| **Tabelas append-only (trigger bloqueia UPDATE/DELETE)** | 4 (`termos_consentimento`, `audit_events`, `access_log`, `lgpd_purge_log`) |
| **Tabelas com hash chain** | 2 (`remanejamentos` se D8 for "paralela" + `audit_events` se D8 for "única") |
| **Tabelas com soft delete** | 13 (todas com PII, exceto `users` que tem explicitamente) |
| **Tabelas com partição** | 2 (`lousa_snapshots`, `lousa_cells` — Sprint 8) |
| **Tabelas de catálogo (seed Sprint 1)** | 5 (`portos`, `turnos`, `funcoes`, `fainas`, `feriados_nacionais`) |
| **Decisões abertas bloqueantes** | 13 (D1-D13) |
| **Risco #1 do plano endereçado** | R1 (OGMO boicota) — `ogmo_notificacoes` unilateral |
| **Risco #3 do plano endereçado** | R3 (MPT invasão) — `audit_events` + `access_log` + `termos_consentimento` |
| **Risco #2 do plano endereçado** | R2 (layout muda) — `layout_fingerprints` |

---

## 8. Próximos passos

1. **Paulo revisa** este dicionário e decide as **13 decisões abertas (D1-D13)**
2. Sobe versão para `status: aprovado` (frontmatter)
3. Coder gera as **migrations Alembic iniciais** baseadas neste DD (Sprint 1
   T1-02)
4. Após migration aplicada em dev, bump para **v1.1** com ajustes
5. `INDICE.md` atualizado para refletir versão ativa

---

*Mantido por SINDESTIVA Bot · última atualização 01/09/2026 · v1 (draft).*
