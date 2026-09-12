-- =============================================================================
-- SINDESTIVA-PE · Postgres init (idempotente — roda em todo startup do container)
--
-- Garante:
--   1. Schema `lousa_main` existe (default do projeto, ADR-002)
--   2. `search_path` default do role inclui `lousa_main` PRIMEIRO (sem isso,
--      Alembic cria tabelas/enums em `public` mesmo com schema=lousa_main)
--   3. Extensões necessárias (pgcrypto para gen_random_uuid, citext p/ emails,
--      pg_trgm p/ índices GIN trigram em busca de funções)
--
-- Por que `ALTER ROLE ... SET search_path`?
--   Alembic/psycopg abrem nova conexão por comando e o search_path volta
--   ao default do role. Setar via ALTER ROLE garante que QUALQUER conexão
--   comece com lousa_main, public. Sem isso, `CREATE TYPE lousa_main.role_enum`
--   passa mas tabelas que referenciam `role_enum` falham porque o parser
--   procura em `public.role_enum` (não acha, porque foi criado em lousa_main).
--
-- Ordem de execução: /docker-entrypoint-initdb.d/*.sql roda em ordem alfabética
-- na primeira inicialização do volume (initdb). Se o volume já existe, esse
-- arquivo NÃO roda — nesse caso rodar manualmente ou recriar o volume.
-- =============================================================================

-- Schema único do projeto (ADR-002)
CREATE SCHEMA IF NOT EXISTS lousa_main;

-- search_path no role (não só na sessão) — crítico pra Alembic/psycopg
ALTER ROLE sindestiva SET search_path = lousa_main, public;

-- Extensões (idempotente)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
