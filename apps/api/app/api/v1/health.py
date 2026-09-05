"""SINDESTIVA-PE · /health endpoint."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.deps import get_db
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="Liveness + DB ping")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Liveness + ping no schema `lousa_main`.

    Sprint 0: ping simples. Sprint 7: adiciona check de Redis + scraper.
    """
    try:
        await db.execute(text("SELECT 1 FROM lousa_main.users LIMIT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001
        db_status = "down"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "sindestiva-api",
        "version": "0.1.0",
        "env": settings.app_env,
        "db": db_status,
    }


@router.get("/diag", summary="Diagnóstico de schema/tabelas (debug)")
async def diag(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Lista schemas, tabelas e current_schema do DB. Usado para
    debugar conexão em produção (Render, etc).
    """
    schemas = [
        r[0]
        for r in (await db.execute(
            text("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name")
        )).all()
    ]
    tables = [
        r[0]
        for r in (await db.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :s ORDER BY table_name"
            ),
            {"s": settings.db_schema},
        )).all()
    ]
    current_schema = (await db.execute(text("SELECT current_schema()"))).scalar()
    # Lista tabelas em TODOS os schemas (para debugar se o alemic_version
    # foi parar em public em vez de lousa_main).
    all_tables = [
        {"schema": r[0], "table": r[1]}
        for r in (await db.execute(text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema NOT IN ('pg_catalog', 'information_schema') "
            "ORDER BY table_schema, table_name"
        ))).all()
    ]
    return {
        "current_schema": current_schema,
        "expected_schema": settings.db_schema,
        "schemas": schemas,
        "tables_in_expected_schema": tables,
        "all_tables": all_tables,
        "database_url_host": settings.database_url_async.split("@")[-1].split("/")[0],
    }


@router.post("/init", summary="Cria schema + tabelas manualmente (admin only)")
async def init_db(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Endpoint administrativo para criar schema + tabelas manualmente.

    Idempotente. Use se o lifespan do FastAPI falhou em criar (ex: cold
    start muito rápido). APÓS Sprint 1, proteger com auth de admin.
    """
    from sqlalchemy import text as sql_text

    # 0. DROP schema (se existir) — reset total. Usar com cuidado.
    # Necessário porque o `create_all` tem ordem estranha para ENUMs
    # quando o schema já tem objetos parciais (tables órfãs com FKs para
    # enums que ainda não foram criados).
    await db.execute(sql_text(f"DROP SCHEMA IF EXISTS {settings.db_schema} CASCADE"))

    # 1. Cria schema
    await db.execute(sql_text(f"CREATE SCHEMA {settings.db_schema}"))

    # 1b. Cria extensions necessárias (gin_trgm_ops, citext, pgcrypto).
    # Algumas tabelas têm índices GIN com `gin_trgm_ops` (DD v1 §3.7-3.8).
    await db.execute(sql_text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    await db.execute(sql_text('CREATE EXTENSION IF NOT EXISTS "citext"'))
    await db.execute(sql_text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))

    # 1c. Cria ENUMs ANTES das tabelas (ordem manual, evita UndefinedObjectError).
    from app.core.database import Base
    import app.models  # noqa: F401  (popula Base.metadata)
    enums_created = []
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            col_type = column.type
            # SQLAlchemy ENUM tem `name` (string) e `enums` (lista de valores).
            if hasattr(col_type, "enums") and hasattr(col_type, "name") and col_type.name:
                enum_full_name = f"{settings.db_schema}.{col_type.name}"
                values = list(col_type.enums)
                if values:
                    vals = ", ".join(f"'{v}'" for v in values)
                    # IF NOT EXISTS via DO block (Postgres não suporta
                    # CREATE TYPE IF NOT EXISTS diretamente até v17)
                    await db.execute(sql_text(
                        f"DO $$ BEGIN "
                        f"  CREATE TYPE {enum_full_name} AS ENUM ({vals}); "
                        f"EXCEPTION WHEN duplicate_object THEN null; "
                        f"END $$;"
                    ))
                    enums_created.append(enum_full_name)
                else:
                    # Fallback: extrai do Python enum
                    py_enum = getattr(col_type, "enum_class", None) or getattr(col_type, "_object_value", None)
                    if py_enum is None and hasattr(col_type, "name"):
                        try:
                            from app.models.enums import ENUM_REGISTRY
                            py_enum = ENUM_REGISTRY.get(col_type.name)
                        except (ImportError, AttributeError):
                            pass
                    if py_enum is not None:
                        vals = ", ".join(f"'{m.name}'" for m in py_enum)
                        await db.execute(sql_text(
                            f"DO $$ BEGIN "
                            f"  CREATE TYPE {enum_full_name} AS ENUM ({vals}); "
                            f"EXCEPTION WHEN duplicate_object THEN null; "
                            f"END $$;"
                        ))
                        enums_created.append(enum_full_name)
    await db.commit()  # fecha transação

    # 2. Cria tabelas via Base.metadata (idempotente)
    from app.core.database import engine as _engine
    async with _engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True)
        )

    # 2b. Workaround: `server_default=text("now() + INTERVAL '5 years'")`
    # no model quebra DDL (text não é castable para timestamptz).
    # Adiciona o default via ALTER TABLE em todas as tabelas que têm
    # o campo `purge_after`. Sprint 1+: reintroduzir via migration Alembic.
    # Encontra tabelas com `purge_after` via information_schema (evita
    # hardcoded list que pode ficar desatualizada).
    purge_tables = [
        r[0] for r in (await db.execute(sql_text(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = :s AND column_name = 'purge_after'"
        ), {"s": settings.db_schema})).all()
    ]
    for table_name in purge_tables:
        await db.execute(sql_text(
            f"ALTER TABLE {settings.db_schema}.{table_name} "
            f"ALTER COLUMN purge_after SET DEFAULT now() + INTERVAL '5 years'"
        ))

    # 3. Verifica resultado
    tables = [
        r[0]
        for r in (await db.execute(sql_text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = :s ORDER BY table_name"
        ), {"s": settings.db_schema})).all()
    ]
    return {
        "schema": settings.db_schema,
        "tables_created": len(tables),
        "tables": tables,
    }


# ---------------------------------------------------------------------------
# SEED de dados de teste (Sprint 0+ — REMOVER em produção após Sprint 1)
# ---------------------------------------------------------------------------


@router.post("/seed", summary="Popula DB com dados de teste (admin only)")
async def seed_db(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Cria dados de teste mínimos para visualizar o sistema.

    Idempotente (ON CONFLICT DO NOTHING). Cria:
      - 1 porto SUAPE
      - 2 turnos (DIURNO 08-16, NOTURNO 20-04)
      - 7 fainas canônicas (Produção, Salário, Sacaria, Veículo, Diversos, Cadastro, Suplementar)
      - 26 funções canônicas
      - 1 fiscal (paulo@pscode.ia.br / sinapse-demo-2026)
      - 1 TPA (matrícula 058)
      - 1 escala de origem (hoje, SUAPE+DIURNO)
      - 10 alocações de teste

    Sprint 1+: PROTEGER com auth admin + REMOVER (ou mover para CLI).
    """
    import bcrypt
    from datetime import date as ddate, datetime as dt, time as dtime, timezone
    from sqlalchemy import text as sql_text

    now = dt.now(tz=timezone.utc)
    today = now.date()
    results: dict[str, list[str]] = {"created": [], "skipped": [], "errors": []}
    error_details: dict[str, str] = {}

    async def upsert(sql: str, params: dict, label: str) -> str:
        """INSERT ... ON CONFLICT DO NOTHING. Retorna 'created' ou 'skipped'."""
        try:
            result = await db.execute(sql_text(sql + " ON CONFLICT DO NOTHING"), params)
            await db.commit()
            status = "created" if result.rowcount > 0 else "skipped"
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            status = "errors"  # chave do dict (plural)
            # Loga o erro completo no log do app (visível no Render)
            log.error(
                "seed.upsert_failed",
                label=label,
                exc_type=type(exc).__name__,
                exc_msg=str(exc),
            )
            error_details[label] = f"{type(exc).__name__}: {exc}"
        results[status].append(label)
        return status

    # 1. Portos
    await upsert(
        "INSERT INTO lousa_main.portos (codigo, nome_completo, cnpj_ogmo, is_active) "
        "VALUES (:c, :n, :cnpj, true)",
        {"c": "SUAPE", "n": "Porto de Suape", "cnpj": "08.978.103/0001-26"},
        "porto SUAPE",
    )
    await upsert(
        "INSERT INTO lousa_main.portos (codigo, nome_completo, cnpj_ogmo, is_active) "
        "VALUES (:c, :n, :cnpj, true)",
        {"c": "RECIFE", "n": "Porto do Recife", "cnpj": "10.504.532/0001-89"},
        "porto RECIFE",
    )

    # 2. Turnos (hora_inicio/hora_fim são TIME — asyncpg exige datetime.time, não string)
    await upsert(
        "INSERT INTO lousa_main.turnos (codigo, nome_exibicao, hora_inicio, hora_fim, duracao_horas) "
        "VALUES (:c, :n, :hi, :hf, :d)",
        {"c": "DIURNO", "n": "Diurno (08h-16h)", "hi": dtime(8, 0), "hf": dtime(16, 0), "d": 8.0},
        "turno DIURNO",
    )
    await upsert(
        "INSERT INTO lousa_main.turnos (codigo, nome_exibicao, hora_inicio, hora_fim, duracao_horas) "
        "VALUES (:c, :n, :hi, :hf, :d)",
        {"c": "NOTURNO", "n": "Noturno (20h-04h)", "hi": dtime(20, 0), "hf": dtime(4, 0), "d": 8.0},
        "turno NOTURNO",
    )

    # 3. Fainas (7 principais do seed — Manoel Costa confirma)
    fainas = [
        ("PRODUCAO", "Produção", 1, "#3b82f6"),
        ("SALARIO", "Salário", 2, "#10b981"),
        ("SACARIA", "Sacaria", 3, "#f59e0b"),
        ("VEICULO", "Veículo", 4, "#8b5cf6"),
        ("DIVERSOS", "Diversos", 5, "#ec4899"),
        ("CADASTRO", "Cadastro", 6, "#06b6d4"),
        ("SUPLEMENTAR", "Suplementar", 7, "#84cc16"),
    ]
    for codigo, nome, ordem, cor in fainas:
        await upsert(
            "INSERT INTO lousa_main.fainas (codigo, nome_exibicao, ordem_lousa, cor_hex, is_active) "
            "VALUES (:c, :n, :o, :cor, true)",
            {"c": codigo, "n": nome, "o": ordem, "cor": cor},
            f"faina {codigo}",
        )

    # 4. Funções (26 canônicas — subset p/ seed; Manoel Costa complementa)
    funcoes = [
        ("MANDO_01", "C/M Geral", 1, "MANDO"),
        ("MANDO_02", "C/M Porão", 2, "MANDO"),
        ("MANDO_03", "C/M Bloco", 3, "MANDO"),
        ("MANDO_04", "C/M Rechego", 4, "MANDO"),
        ("MANDO_05", "C/M Cons.", 5, "MANDO"),
        ("MANDO_06", "Supervisor", 6, "MANDO"),
        ("TERNO_01", "Porão", 7, "TERNO"),
        ("TERNO_02", "Bloco MAX", 8, "TERNO"),
        ("TERNO_03", "Bloco", 9, "TERNO"),
        ("TERNO_04", "Rechego", 10, "TERNO"),
        ("TERNO_05", "Cons.", 11, "TERNO"),
        ("TERNO_06", "Ship Loader", 12, "TERNO"),
        ("TECNICA_01", "Sinaleiro", 13, "TECNICA"),
        ("TECNICA_02", "Guincho A", 14, "TECNICA"),
        ("TECNICA_03", "Guincho B", 15, "TECNICA"),
        ("TECNICA_04", "Emp. GP", 16, "TECNICA"),
        ("TECNICA_05", "Emp. PP", 17, "TECNICA"),
        ("TECNICA_06", "V. Pesado", 18, "TECNICA"),
        ("TECNICA_07", "V. Leve", 19, "TECNICA"),
        ("TECNICA_08", "Manobrista", 20, "TECNICA"),
        ("TECNICA_09", "Transp.", 21, "TECNICA"),
        ("TECNICA_10", "Pá Mec.", 22, "TECNICA"),
        ("VIGIA_01", "Vigia Porto", 23, "VIGIA"),
        ("VIGIA_02", "Vigia Cais", 24, "VIGIA"),
    ]
    for codigo, nome, ordem, cat in funcoes:
        await upsert(
            "INSERT INTO lousa_main.funcoes (codigo, nome_exibicao, categoria, ordem_lousa, is_active) "
            "VALUES (:c, :n, :cat, :o, true)",
            {"c": codigo, "n": nome, "cat": cat, "o": ordem},
            f"funcao {codigo}",
        )

    # 5. User fiscal (paulo@pscode.ia.br)
    # `purge_after` é NOT NULL (LGPD 5a default). Calcula 5 anos no futuro.
    pwd_hash = bcrypt.hashpw(b"sinapse-demo-2026", bcrypt.gensalt()).decode()
    await upsert(
        "INSERT INTO lousa_main.users (email, telefone, password_hash, role, status, "
        "accepted_terms_at, accepted_terms_version, purge_after) "
        "VALUES (:email, :tel, :pwd, 'FISCAL'::role_enum, 'ATIVO'::user_status_enum, "
        ":now, '1.0', :purge)",
        {"email": "paulo@pscode.ia.br", "tel": "+5581999998888", "pwd": pwd_hash,
         "now": now, "purge": now.replace(year=now.year + 5)},
        "user paulo@pscode.ia.br",
    )

    # 6. User TPA (matricula 058)
    pwd_hash_tpa = bcrypt.hashpw(b"sinapse-demo-2026", bcrypt.gensalt()).decode()
    await upsert(
        "INSERT INTO lousa_main.users (email, telefone, password_hash, role, status, "
        "accepted_terms_at, accepted_terms_version, purge_after) "
        "VALUES (:email, :tel, :pwd, 'TPA'::role_enum, 'ATIVO'::user_status_enum, "
        ":now, '1.0', :purge)",
        {"email": "tpa058@ogmo-pe.com.br", "tel": "+5581988887777", "pwd": pwd_hash_tpa,
         "now": now, "purge": now.replace(year=now.year + 5)},
        "user tpa058",
    )

    # 7. Fiscal profile (linka user FISCAL ao perfil Fiscal)
    # Modelo: cpf, matricula_sindicato, porto_id, turno_id, data_inicio
    # são NOT NULL — populamos todos.
    await db.commit()
    fiscal_user_id = (await db.execute(sql_text(
        "SELECT id FROM lousa_main.users WHERE email = :email"
    ), {"email": "paulo@pscode.ia.br"})).scalar()
    suape_id_pre = (await db.execute(sql_text(
        "SELECT id FROM lousa_main.portos WHERE codigo = 'SUAPE'"
    ))).scalar()
    diurno_id_pre = (await db.execute(sql_text(
        "SELECT id FROM lousa_main.turnos WHERE codigo = 'DIURNO'"
    ))).scalar()
    if fiscal_user_id and suape_id_pre and diurno_id_pre:
        await upsert(
            "INSERT INTO lousa_main.fiscais (user_id, cpf, matricula_sindicato, "
            "nome_completo, telefone, porto_id, turno_id, status, data_inicio, "
            "purge_after) "
            "VALUES (:uid, :cpf, :mat, :nome, :tel, :p, :t, "
            "'ATIVO'::fiscal_status_enum, :di, :purge)",
            {"uid": fiscal_user_id, "cpf": "111.222.333-96", "mat": "F-001",
             "nome": "Paulo Siqueira", "tel": "+5581999998888",
             "p": suape_id_pre, "t": diurno_id_pre, "di": today,
             "purge": now.replace(year=now.year + 5)},
            "fiscal Paulo Siqueira",
        )

    # 8. TPA profile (linka user TPA ao perfil TPA)
    # Modelo: matricula_ogmo (não matricula), status_cadastro (não status),
    # funcao_base_id + categoria são NOT NULL.
    tpa_user_id = (await db.execute(sql_text(
        "SELECT id FROM lousa_main.users WHERE email = :email"
    ), {"email": "tpa058@ogmo-pe.com.br"})).scalar()
    funcao_base_id = (await db.execute(sql_text(
        "SELECT id FROM lousa_main.funcoes WHERE codigo = 'MANDO_01'"
    ))).scalar()
    if tpa_user_id and funcao_base_id:
        await upsert(
            "INSERT INTO lousa_main.tpas (user_id, cpf, nome_completo, "
            "matricula_ogmo, telefone, funcao_base_id, categoria, "
            "data_nascimento, status_cadastro, purge_after) "
            "VALUES (:uid, :cpf, :nome, :mat, :tel, :fb, :cat, :dn, "
            "'ATIVO'::tpa_status_enum, :purge)",
            {"uid": tpa_user_id, "cpf": "123.456.789-00",
             "nome": "João da Silva Santos", "mat": "OG-058",
             "tel": "+5581988887777", "fb": funcao_base_id, "cat": "MANDO",
             "dn": ddate(1985, 3, 15),
             "purge": now.replace(year=now.year + 5)},
            "tpa João da Silva (OG-058)",
        )

    # 9. Lousa_escala_origem (hoje, SUAPE+DIURNO)
    suape_id = (await db.execute(sql_text(
        "SELECT id FROM lousa_main.portos WHERE codigo = 'SUAPE'"
    ))).scalar()
    diurno_id = (await db.execute(sql_text(
        "SELECT id FROM lousa_main.turnos WHERE codigo = 'DIURNO'"
    ))).scalar()

    if suape_id and diurno_id:
        await upsert(
            "INSERT INTO lousa_main.lousa_escala_origem (fonte, porto_id, turno_id, "
            "data_referencia, url_origem, content_hash, payload_jsonb, duracao_ms, status) "
            "VALUES ('TPA'::fonte_escala_enum, :p, :t, :d, :url, :hash, '{}'::jsonb, 1200, "
            "'SUCESSO'::status_scraping_enum)",
            {"p": suape_id, "t": diurno_id, "d": today,
             "url": "http://tpa.ogmosuape.com.br/web/lousa_estiva",
             "hash": "a" * 64},
            "lousa_escala_origem (SUAPE+DIURNO)",
        )

    # 10. Lousa_alocacao (10 alocações de teste)
    escala_id = (await db.execute(sql_text(
        "SELECT id FROM lousa_main.lousa_escala_origem "
        "WHERE fonte = 'TPA' AND data_referencia = :d "
        "ORDER BY created_at DESC LIMIT 1"
    ), {"d": today})).scalar()

    if escala_id and suape_id and diurno_id:
        alocacoes_teste = [
            ("PRODUCAO", "MANDO_01", "OG-058"),
            ("PRODUCAO", "MANDO_02", "OG-100"),
            ("PRODUCAO", "MANDO_03", "OG-133"),
            ("SALARIO", "MANDO_01", "OG-058"),
            ("SALARIO", "TERNO_01", "OG-200"),
            ("SACARIA", "MANDO_01", "OG-058"),
            ("SACARIA", "TECNICA_01", "OG-300"),
            ("VEICULO", "TECNICA_06", "OG-400"),
            ("CADASTRO", "VIGIA_01", "OG-500"),
            ("SUPLEMENTAR", "MANDO_06", "OG-058"),
        ]
        for faina, funcao, mat in alocacoes_teste:
            faina_id = (await db.execute(sql_text(
                "SELECT id FROM lousa_main.fainas WHERE codigo = :c"
            ), {"c": faina})).scalar()
            funcao_id = (await db.execute(sql_text(
                "SELECT id FROM lousa_main.funcoes WHERE codigo = :c"
            ), {"c": funcao})).scalar()
            if faina_id and funcao_id:
                categoria = funcao.split("_")[0]  # MANDO/TERNO/TECNICA/VIGIA
                fk_mando = 1 if categoria == "MANDO" else None
                fk_terno = 1 if categoria == "TERNO" else None
                fk_tecnica = 1 if categoria == "TECNICA" else None
                fk_vigia = 1 if categoria == "VIGIA" else None
                await upsert(
                    "INSERT INTO lousa_main.lousa_alocacao (escala_origem_id, porto_id, "
                    "turno_id, faina_id, funcao_id, data_referencia, trabalhador_matricula, "
                    "fk_mando, fk_terno, fk_tecnica, fk_vigia, scraped_at, created_at) "
                    "VALUES (:e, :p, :t, :fa, :fu, :d, :mat, :m, :te, :tc, :v, :now, :now)",
                    {"e": escala_id, "p": suape_id, "t": diurno_id,
                     "fa": faina_id, "fu": funcao_id, "d": today, "mat": mat,
                     "m": fk_mando, "te": fk_terno, "tc": fk_tecnica, "v": fk_vigia,
                     "now": now},
                    f"alocacao {faina}+{funcao}+{mat}",
                )

    return {
        "ok": True,
        "created": results["created"],
        "skipped": results["skipped"],
        "errors": results["errors"],
        "error_details": error_details,
        "test_credentials": {
            "fiscal": {"email": "paulo@pscode.ia.br", "senha": "sinapse-demo-2026"},
            "tpa": {"email": "tpa058@ogmo-pe.com.br", "senha": "sinapse-demo-2026"},
        },
    }


@router.get("/counts", summary="Conta registros em cada tabela (debug)")
async def counts(db: AsyncSession = Depends(get_db)) -> dict[str, int]:
    """Retorna COUNT(*) de cada tabela útil (debug de seed/scraper)."""
    from sqlalchemy import text as sql_text
    tables = [
        "users", "fiscais", "tpas", "portos", "turnos", "fainas", "funcoes",
        "lousa_escala_origem", "lousa_alocacao", "remanejamentos",
        "hash_chain_checkpoint", "audit_events",
    ]
    result = {}
    for t in tables:
        n = (await db.execute(sql_text(f"SELECT COUNT(*) FROM lousa_main.{t}"))).scalar()
        result[t] = n
    return result


@router.post("/dedupe-users", summary="Remove users duplicados (mesmo email) e adiciona UNIQUE")
async def dedupe_users(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Limpa duplicatas de `users` criadas por runs antigos do seed (sem
    UNIQUE constraint) e adiciona `UNIQUE` no `email` (citext).

    Estratégia:
      1. Para cada email duplicado, mantém o registro MAIS ANTIGO
         (menor `id` castado como uuid, = criação cronológica).
      2. Deleta fiscais/tpas órfãos (FK ondelete=RESTRICT exige limpar
         filhos antes de deletar o user).
      3. Cria índice UNIQUE em `users(email)`.

    Idempotente. Sprint 1+: mover para migration Alembic e remover.
    """
    from sqlalchemy import text as sql_text
    from fastapi import HTTPException

    try:
        return await _dedupe_users_impl(db, sql_text)
    except Exception as exc:  # noqa: BLE001
        log.error("dedupe_users.failed", exc_type=type(exc).__name__, exc_msg=str(exc))
        raise HTTPException(
            status_code=500,
            detail={"code": "DEDUPE_FAILED", "message": f"{type(exc).__name__}: {exc}"},
        ) from exc


async def _dedupe_users_impl(db: AsyncSession, sql_text) -> dict[str, object]:
    log.info("dedupe_users.start")

    # 1. Listar duplicatas ANTES de deletar (para reportar).
    dupes = (await db.execute(sql_text(
        "SELECT email, COUNT(*) AS n FROM lousa_main.users "
        "WHERE email IS NOT NULL "
        "GROUP BY email HAVING COUNT(*) > 1"
    ))).all()
    dupe_summary = [{"email": r[0], "count": r[1]} for r in dupes]

    # 2. Deletar fiscais/tpas dos users que serão removidos (cascata manual).
    # Mantém o user com MENOR id::text (= criado primeiro; MIN(uuid) não existe
    # no Postgres, então ordenamos pelo id lexicográfico via text).
    fiscais_deleted = (await db.execute(sql_text(
        "DELETE FROM lousa_main.fiscais "
        "WHERE user_id IN ("
        "  SELECT id FROM lousa_main.users "
        "  WHERE email IS NOT NULL "
        "  AND id::text NOT IN ("
        "    SELECT MIN(id::text) FROM lousa_main.users "
        "    WHERE email IS NOT NULL GROUP BY email"
        "  )"
        ")"
    ))).rowcount
    tpas_deleted = (await db.execute(sql_text(
        "DELETE FROM lousa_main.tpas "
        "WHERE user_id IN ("
        "  SELECT id FROM lousa_main.users "
        "  WHERE email IS NOT NULL "
        "  AND id::text NOT IN ("
        "    SELECT MIN(id::text) FROM lousa_main.users "
        "    WHERE email IS NOT NULL GROUP BY email"
        "  )"
        ")"
    ))).rowcount
    await db.commit()

    # 3. Deletar users duplicados.
    deleted = (await db.execute(sql_text(
        "DELETE FROM lousa_main.users "
        "WHERE email IS NOT NULL "
        "AND id::text NOT IN ("
        "  SELECT MIN(id::text) FROM lousa_main.users "
        "  WHERE email IS NOT NULL GROUP BY email"
        ")"
    ))).rowcount
    await db.commit()

    # 4. Cria índice UNIQUE (IF NOT EXISTS, idempotente).
    try:
        await db.execute(sql_text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email "
            "ON lousa_main.users (email)"
        ))
        await db.commit()
        unique_status = "created"
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        unique_status = f"error: {exc!s}"

    # 5. Counts pós-cleanup.
    after = (await db.execute(sql_text(
        "SELECT COUNT(*) FROM lousa_main.users"
    ))).scalar()

    log.info("dedupe_users.done", deleted=deleted, after=after)
    return {
        "ok": True,
        "duplicates_found": dupe_summary,
        "fiscais_deleted": fiscais_deleted,
        "tpas_deleted": tpas_deleted,
        "users_deleted": deleted,
        "users_remaining": after,
        "unique_index": unique_status,
    }
