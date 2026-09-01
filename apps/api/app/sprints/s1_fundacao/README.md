# Sprint 1 — Fundação (14-20/09/2026)

## Marco: M1 Centro autenticado

### Entregáveis
- `apps/api/app/` estrutura modular (este repositório)
- Migration 0001 com 25 tabelas (DD v1 §3)
- Auth NextAuth v5 + JWT 8h
- Seed dos 5 catálogos (portos, turnos, funcoes, fainas, feriados)

### Tabelas tocadas
**TODAS** — migration 0001 é a foundation. Seeds tocam:
- `portos` (SUAPE, RECIFE)
- `turnos` (DIURNO 08-16, NOTURNO 20-04)
- `funcoes` (26 placeholders, D5)
- `fainas` (10 placeholders, D5)
- `feriados_nacionais` (15 hard-coded)

### Tarefas
- T1-01: setup ambiente (Docker Compose, .env) — **OK**
- T1-02: modelagem do banco (DD v1 → migration 0001) — **OK** (este repo)
- T1-03: seed dos 5 catálogos — **OK** (`scripts/seed_catalogos.py`)
- T1-04: auth NextAuth v5 — placeholder
- T1-05: RBAC 3 roles (Fiscal, Dirigente, TPA) — enum pronto
- T1-06: configurar CSRF + CORS — Sprint 7
- T1-07: middleware `request_id` — OK (`app/core/logging.py`)
- T1-08: dependência `get_current_user` — OK (`app/core/security.py`)
- T1-09: página de login estilizada — frontend (apps/web)
- T1-10: termo LGPD v1 — Sprint 3
- T1-11: carta formal OGMO — K-7 (Sprint 0)

### Como rodar local

```bash
# 1. Subir Postgres + Redis
pnpm db:up   # ou docker compose -f infra/docker-compose.yml up -d postgres redis

# 2. Aplicar migrations
cd apps/api && alembic upgrade head

# 3. Seed catálogos
python apps/api/scripts/seed_catalogos.py

# 4. Subir API
uvicorn app.main:app --reload --port 8000
```

### Decisões abertas a sinalizar

- **D1** TPA password vs OTP: seed atual assume `password_hash = NULL`
  para TPA (constraint `ck_users_password_for_non_tpa`).
- **D4** Turno intermediário: seed atual tem 2 turnos; adicionar
  3º se Manoel confirmar.
- **D5** 10 fainas e 26 funções: seed atual tem placeholders
  explícitos ("Técnica 11 (a definir c/ Manoel)").
