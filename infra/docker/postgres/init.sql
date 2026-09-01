-- =============================================================================
-- SINDESTIVA-PE · Postgres init (executado no primeiro start do container)
-- Cria extensões úteis e schema padrão. Tabelas/models são criadas via
-- migrations SQLAlchemy/Alembic (NÃO escrever DDL aqui).
-- =============================================================================

-- Extensões
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";       -- digest() pra hash chain
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- busca fuzzy em TPAs

-- Schema principal (MVP = schema único, ADR-002)
CREATE SCHEMA IF NOT EXISTS lousa_main;
SET search_path TO lousa_main, public;

-- Locale
SET lc_messages = 'pt_BR.UTF-8';
SET lc_monetary = 'pt_BR.UTF-8';
SET lc_numeric = 'pt_BR.UTF-8';
SET lc_time = 'pt_BR.UTF-8';

-- Timezone
SET timezone = 'America/Recife';

-- Comentário no schema pra documentar a separação multi-tenant futura
COMMENT ON SCHEMA lousa_main IS
  'Schema principal do MVP SINDESTIVA-PE (single-tenant). Em Fase 3 vira multi-tenant via schema-per-cliente.';
