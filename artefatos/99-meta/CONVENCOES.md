---
id: CONVENCOES
versao: 1
status: ativo
data_criacao: 2026-09-01
manter_ate: enquanto v1 do DD estiver ativa
---

# Convenções do Dicionário de Dados · Lousa Digital

> Este documento define **as regras de modelagem e o workflow de evolução** do
> `DD-lousa-sindestiva-v{N}.md`. Toda nova tabela/coluna/índice deve respeitar
> as convenções abaixo. Mudanças nas próprias convenções exigem aprovação do
> **Paulo Siqueira** (sponsor técnico + DPO).

---

## 1. Stack de banco (referência)

| Item | Decisão | ADR |
|---|---|---|
| SGBD | **PostgreSQL 17** | — |
| ORM | **SQLAlchemy 2.0** (Python) | — |
| Migrations | **Alembic** | — |
| Schema | **`lousa_main`** (MVP, schema único) | ADR-002 |
| Extensões obrigatórias | `pgcrypto` (`gen_random_uuid()`) | — |
| Extensões úteis | `citext` (CPF case-insensitive), `pg_trgm` (busca fuzzy em TPAs) | — |

> Multi-tenant por schema entra em **Fase 3** (modelo B2B para outros OGMOs).
> A partir daí, o schema passa a ser `lousa_<ogmo_slug>`.

---

## 2. Nomenclatura

### 2.1 Identificadores (tabelas, colunas, índices)

| Elemento | Convenção | Exemplo |
|---|---|---|
| Tabelas | `snake_case` no **plural** | `users`, `remanejamentos`, `lousa_cells` |
| Colunas | `snake_case` no **singular** | `created_at`, `cpf`, `matricula_ogmo` |
| PK | sempre `id` (sem prefixo) | `id uuid` |
| FK | `<tabela_referenciada_singular>_id` | `user_id`, `tpa_id`, `fiscal_id`, `porto_id` |
| Timestamps | sufixo `_at`, todos `timestamptz` | `created_at`, `updated_at`, `deleted_at`, `confirmed_at` |
| Booleanos | prefixo `is_` / `has_` ou sufixo `_flag` | `is_active`, `has_consent` |
| Enums | sufixo `_enum` no tipo, sufixo `_at` no campo data | `status_remanejamento_enum`, `ack_at` |

### 2.2 Índices e constraints

| Tipo | Convenção | Exemplo |
|---|---|---|
| Índice simples | `idx_<tabela>_<coluna(s)>` | `idx_lousa_snapshots_porto_turno_created` |
| Índice único | `uq_<tabela>_<coluna(s)>` | `uq_users_email`, `uq_tpas_cpf`, `uq_tpas_matricula_ogmo` |
| Check | `ck_<tabela>_<regra_curta>` | `ck_remanejamentos_tpa_in_or_out` |
| Foreign key | `fk_<tabela>_<coluna>_<referencia>` (opcional, geralmente nomeado pelo SGBD) | `fk_lousa_cells_tpa_id` |
| Trigger | `tg_<tabela>_<evento>` | `tg_audit_events_block_update` |

### 2.3 Domínio (campos sensíveis / LGPD)

| Domínio | Tipo PostgreSQL | Observação |
|---|---|---|
| `cpf` | `citext` (com `CHECK` de formato) | `XXX.XXX.XXX-XX` ou só dígitos; precisa de `CHECK (cpf ~ '^\d{11}$')` |
| `telefone` | `text` | Validado via lib Python; normalizar para `+55DDXXXXXXXXX` |
| `email` | `citext` (case-insensitive) | `CHECK (email ~* '^[^@]+@[^@]+\.[^@]+$')` |
| `matricula_ogmo` | `text` (não numérico: pode ter zeros à esquerda) | `CHECK (length(matricula_ogmo) BETWEEN 1 AND 10)` |
| `hash_sha256` | `char(64)` | Hex de 64 chars; lowercase enforced |
| `versao_termo` | `text` | SemVer-like: `v1.0`, `v1.1` |
| `status_*` | enum customizado (`CREATE TYPE ... AS ENUM (...)`) | Sempre que o domínio for fechado |

---

## 3. Padrões de coluna (todas as tabelas)

Toda tabela de domínio deve ter, no mínimo, estes campos (criados pela
`mixin.TimestampMixin` e `mixin.SoftDeleteMixin` em SQLAlchemy):

| Coluna | Tipo | Default | Obrigatório? | Notas |
|---|---|---|---|---|
| `id` | `uuid` | `gen_random_uuid()` | ✓ | PK |
| `created_at` | `timestamptz` | `now()` | ✓ | Auditoria implícita (criação) |
| `updated_at` | `timestamptz` | `now()` | ✓ | Atualizado por trigger `BEFORE UPDATE` |
| `deleted_at` | `timestamptz` | `NULL` | ✗ (soft delete) | Soft delete; índice parcial `WHERE deleted_at IS NULL` quando a tabela tem LGPD |

**Timestamps são SEMPRE `timestamptz`** (nunca `timestamp` sem TZ — pegadinha
clássica em deployments multi-fuso). Aplicar mesmo em campos de domínio
(`confirmed_at`, `ack_at`, `notified_at`).

### 3.1 Convenção para `purge_after` (LGPD)

Tabelas com dado pessoal devem ter um campo `purge_after timestamptz` (gerado
a partir de `created_at + INTERVAL '24 months'` por trigger ou pela aplicação
no INSERT). O **job diário de purge** (Sprint 6 T6-06) usa esse campo para
identificar linhas elegíveis a `DELETE` (com log em `lgpd_purge_log`).

### 3.2 Convenção para hash chain (LGPD/auditoria)

Tabelas marcadas como **auditáveis** têm **trigger BEFORE UPDATE/DELETE** que
bloqueia a operação (`raise exception 'append-only table'`). Omitido apenas
em `lousa_snapshots` (cresce indefinidamente — soft delete + partição por
mês é a estratégia).

---

## 4. Relacionamentos

| Cardinalidade | Notação | Exemplo |
|---|---|---|
| 1:1 | `users 1—1 tpas` (chave em `tpas.user_id UNIQUE NOT NULL`) | `users × tpas` |
| 1:N | `portos 1—N lousa_snapshots` | `portos × lousa_snapshots` |
| N:N | tabela de junção explícita: `<a>_<b>` | `user_roles` (não usado no MVP — role é enum) |

### 4.1 Política de `ON DELETE` (referencial)

| Caso | Política | Justificativa |
|---|---|---|
| Dado pessoal (TPA, Fiscal, Dirigente) | `ON DELETE RESTRICT` (FK) + `soft delete` no app | LGPD — exclusão é via `lgpd_solicitacoes`, não cascade |
| Dado de catálogo (Porto, Turno, Funcao, Faina) | `ON DELETE RESTRICT` | Catálogo é imutável em produção (seed) |
| Snapshot / log | `ON DELETE CASCADE` permitido apenas se pai é sessão/scope | `remanejamento_historico.remanejamento_id` cascade? **NÃO** — append-only |
| Audit | `ON DELETE RESTRICT` + trigger bloqueia | Imutável |

> Regra de ouro: **nenhum `ON DELETE CASCADE` em dados pessoais ou de
> auditoria**. Exclusões precisam de workflow explícito (`lgpd_solicitacoes`).

---

## 5. Padrão de documentação por tabela

Para CADA tabela do dicionário, manter a estrutura:

```markdown
### 3.N <nome_tabela>
- **Propósito:** 1 linha descrevendo o que a tabela guarda
- **Volume esperado:** ordem de grandeza (1k / 100k / 1M linhas/ano)
- **LGPD:** sim/não · quais campos são pessoais
- **Retenção:** 24m padrão / 5a para auditoria / indefinida
- **Soft delete:** sim/não · campo `deleted_at`
- **Hash chain:** sim/não · tabela auditável ou não

| Coluna | Tipo PG | NOT NULL | Default | FK | Índice | Descrição |
|---|---|---|---|---|---|---|
| id | uuid | ✓ | gen_random_uuid() |  | PK | |
| ... | | | | | | |

**Constraints:** `UNIQUE`, `CHECK`, `FK`
**Índices:** além dos óbvios
**Observações:** soft-delete, hash chain, particionamento
```

---

## 6. Workflow de evolução do dicionário

### 6.1 Adicionar nova tabela

1. Abrir branch `docs/dd-v{N+1}-{slug}` (ex: `docs/dd-v2-pagamentos`)
2. Editar `DD-lousa-sindestiva-v{N}.md` (incrementar para `v{N+1}.md` se
   mudança for breaking) **ou** adicionar seção nova em `v{N}.md` se
   aditiva
3. Atualizar `INDICE.md` para apontar a versão ativa
4. Atualizar `DD-lousa-sindestiva-changelog.md` (entrada nova)
5. PR com tag `docs` + `dd` + review do Paulo
6. Após merge, marcar versão anterior como `deprecated` (não apagar)

### 6.2 Mudança breaking (renomear coluna, mudar tipo)

- **NUNCA** renomear coluna em produção sem migration reversível
- Versão do DD sobe (v1 → v2)
- Changelog registra `BREAKING` na entrada
- ADR correspondente deve ser criado em `docs/ADR/`

### 6.3 Quem aprova

| Tipo de mudança | Aprovador |
|---|---|
| Aditiva (nova tabela, nova coluna nullable) | **Paulo** (1 review) |
| Breaking (rename, type change) | **Paulo + Josias** (sponsor cliente precisa saber) |
| LGPD-impactante (mudança de retenção, base legal) | **Paulo + Advogado trabalhista** |
| Multi-tenant (Fase 3) | **Paulo + Josias + Steering committee** |

---

## 7. Versionamento

| Versão | Status | Período | Como saber que está ativa |
|---|---|---|---|
| `v1` | ativa | 01/09/2026 → ~Fev/2027 | `INDICE.md` aponta pra `DD-lousa-sindestiva-v1.md` |
| `v1.1` | draft (minor) | — | frontmatter `status: draft` |
| `v2` | deprecated | pós Go-Live | arquivo movido para `artefatos/05-dicionario-dados/historico/` |

> O `INDICE.md` aponta **sempre** para a versão ativa. Versões deprecated
> ficam em `historico/` e mantêm link reverso no changelog.

---

## 8. Anti-padrões (NÃO fazer)

- ❌ Coluna `jsonb` "genérica" sem justificativa (usar `jsonb` apenas para
  payload de eventos de scraping e webhook — caso conhecido)
- ❌ `text` para campos com domínio finito (usar `enum`)
- ❌ `timestamp without time zone` em qualquer coluna
- ❌ `varchar(N)` arbitrário sem justificativa (preferir `text` com `CHECK` de
  tamanho, ou `citext` para e-mail/CPF)
- ❌ `numeric` sem precisão definida
- ❌ `boolean` com semântica dupla (usar 2 colunas ou enum)
- ❌ Índices em colunas de baixa cardinalidade sem motivo (ex: `is_active`
  com 95% true)
- ❌ Triggers que mutam a linha sendo inserida (causa recursão; usar
  `BEFORE` com `WHEN` ou coluna calculada)
- ❌ Cascade delete em tabelas com dado pessoal

---

*Mantido por SINDESTIVA Bot · aprovado por Paulo Siqueira em 01/09/2026 · v1.*
