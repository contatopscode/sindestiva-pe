"""SINDESTIVA-PE · Fixtures compartilhadas pelos testes (Sprint 1+).

Re-exporta fixtures de fakes (`fakes_path`, `fake_http_factory`,
`FakeHttpClient`) usadas por `test_scraping.py` (Sprint 2), além das
fixtures novas de Sprint 1 (auth + LGPD + models).

Convenção deste conftest:
  - `db_session` (function scope): usa o engine global de `lousa_main`
    (mesmo do dev/API live). Cleanup explícito por DELETE nas tabelas
    tocadas (FK-safe order). Isola testes sem mexer no schema (DDL).

    Por que não criar schema descartável `lousa_main_test_*`? Os
    models têm `Text(64)` que é inválido em Postgres puro (precisa
    ser `String(64)` ou `CHAR(64)`). A migration 0001 cria via raw SQL
    com `CHAR(64)`, então o DDL real diverge dos models. `create_all`
    falha. Usar o schema real (lousa_main) com cleanup explícito é
    mais fiel ao que a migration cria. TODO: alinhar models e
    migration (DDL drift — ver CHECKPOINT bugs).

  - `client` (session scope): `httpx.AsyncClient` apontando pra API
    live em `http://127.0.0.1:8765` (briefing: API rodando).
  - `seed_users`: cria os 3 users (Paulo/Manoel/Josias) em lousa_main
    (com cleanup antes pra idempotência).
  - `api_token_paulo` etc: tokens via POST /auth/login no client.

Pega-dica (cross-projeto, MEMORY): NullPool evita "Future attached to
a different loop" entre pytest-asyncio e engine global. Aqui NÃO
recriamos o engine — reusamos o global de `app.core.database` pra
manter a paridade com o que a API live usa.
"""
from __future__ import annotations

import os
import secrets
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import session_scope
from app.core.security import hash_password
from app.models import (
    LgpdPurgeLog,
    LgpdSolicitacao,
    Remanejamento,
    RemanejamentoHistorico,
    RoleEnum,
    TermoConsentimento,
    Tpa,
    User,
    UserStatusEnum,
)

# ---------------------------------------------------------------------------
# Paths & fakes (legado — usado por test_scraping.py do Sprint 2)
# ---------------------------------------------------------------------------

FAKES_DIR = Path(__file__).resolve().parent / "fakes"


@pytest.fixture
def fakes_path() -> Path:
    """Diretório `tests/fakes/` (path absoluto)."""
    return FAKES_DIR


class _FakeResponse:
    """Resposta HTTP mínima que o scraper usa (apenas `text`)."""

    def __init__(self, text: str) -> None:
        self.text = text


class FakeHttpClient:
    """Cliente HTTP mock que retorna HTML estático baseado na URL."""

    def __init__(
        self, html: str | None = None, *, raise_exc: Exception | None = None
    ) -> None:
        self.html = html
        self.raise_exc = raise_exc
        self.calls: list[str] = []

    async def get(self, url: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(url)
        if self.raise_exc is not None:
            raise self.raise_exc
        if self.html is None:
            raise RuntimeError("FakeHttpClient sem HTML configurado")
        return _FakeResponse(self.html)


@pytest.fixture
def fake_http_factory():
    """Factory de `FakeHttpClient` (retorna callable)."""

    def _make(
        html: str | None = None, *, raise_exc: Exception | None = None
    ) -> FakeHttpClient:
        return FakeHttpClient(html=html, raise_exc=raise_exc)

    return _make

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("SINDESTIVA_API_URL", "http://127.0.0.1:8765")
SEED_PASSWORD = "sindestiva-dev-2026"
SEED_USERS = [
    ("paulo@pscode.ia.br", "DIRIGENTE", "+5581999990001"),
    ("manoel@sindestiva-pe.com.br", "FISCAL", "+5581999990002"),
    ("josias@sindestiva-pe.com.br", "DIRIGENTE", "+5581999990003"),
]

# Tabelas tocadas pelos testes do Sprint 1.
# NÃO limpamos: `remanejamentos`, `remanejamento_historico` (append-only),
# `tpas` (FK reversa de remanejamentos), `fiscais` (FK reversa de
# remanejamentos + FK a users com RESTRICT), `lgpd_purge_log`
# (trigger `tg_purge_log_block_update/delete`), `audit_events`
# (append-only via `tg_audit_block_update/delete`).
# Limpamos: termos_consentimento, lgpd_solicitacoes, dirigentes,
# users DIRIGENTE (Paulo/Josias). Manoel (FISCAL) e os 2 TPAs
# permanecem — Manoel tem fiscais+remanejamentos linkados.
TABLES_TO_CLEAN = [
    "termos_consentimento",
    "lgpd_solicitacoes",
    "dirigentes",
]


# ---------------------------------------------------------------------------
# Cleanup helper
# ---------------------------------------------------------------------------

async def _clean_db() -> None:
    """DELETE nas tabelas que PODEM ser limpas (LGPD + dirigentes).

    Não apagamos `users` porque `access_log` (append-only) tem FK
    RESTRICT pra `users.id`. O fixture `seed_users` faz upsert por
    email — Paulo/Manoel/Josias existentes são ATUALIZADOS (password
    reset, status ATIVO, failed_login_count=0, blocked_until=NULL)
    ao invés de duplicados. Idempotente.

    Outras tabelas append-only (audit_events, remanejamentos,
    remanejamento_historico, lgpd_purge_log, tpas) também ficam
    intocadas — ver TABLES_TO_CLEAN.

    Usa um engine isolado (NullPool) pra evitar deadlock com o engine
    global que a API live também usa — em testes integrados, o
    scheduler de scraping da API está escrevendo em paralelo.
    """
    from sqlalchemy.ext.asyncio import create_async_engine  # noqa: PLC0415
    from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: PLC0415
    from sqlalchemy.pool import NullPool  # noqa: PLC0415

    engine = create_async_engine(settings.database_url_async, poolclass=NullPool)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        async with Session() as session:
            for table in TABLES_TO_CLEAN:
                await session.execute(text(f"DELETE FROM lousa_main.{table}"))
            await session.commit()
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Session de DB (função-scoped, isolation por DELETE)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Sessão async contra `lousa_main` com cleanup antes do teste.

    Padrão: cleanup explícito (não transação com rollback) porque os
    testes podem disparar triggers (audit_events, append-only) que
    não fazem sentido reverter.
    """
    await _clean_db()
    async with session_scope() as session:
        yield session


# ---------------------------------------------------------------------------
# Seed users
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def seed_users(db_session: AsyncSession) -> list[User]:
    """Cria os 3 users seed (Paulo/Manoel/Josias) em lousa_main.

    Idempotente: se user já existe (por email), atualiza password_hash
    e status ao invés de duplicar. Manoel já existe no seed de dev
    (não pode ser deletado por causa de FK), então é atualizado.
    Paulo/Josias são DIRIGENTE — o cleanup apaga antes do seed.

    Senha: `sindestiva-dev-2026` (mesma do dev, hash bcrypt 12 rounds).
    """
    from sqlalchemy import select  # noqa: PLC0415

    now = datetime.now(tz=timezone.utc)
    users: list[User] = []
    for email, role, telefone in SEED_USERS:
        # Upsert por email (citext é case-insensitive nativo).
        stmt = select(User).where(User.email == email)
        result = await db_session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.password_hash = hash_password(SEED_PASSWORD)
            existing.telefone = telefone
            existing.status = UserStatusEnum.ATIVO
            existing.failed_login_count = 0
            existing.blocked_until = None
            users.append(existing)
        else:
            u = User(
                email=email,
                telefone=telefone,
                password_hash=hash_password(SEED_PASSWORD),
                role=RoleEnum(role),
                status=UserStatusEnum.ATIVO,
                accepted_terms_at=now,
                accepted_terms_version="1.0",
            )
            db_session.add(u)
            users.append(u)
    await db_session.commit()
    for u in users:
        await db_session.refresh(u)
    return users


@pytest_asyncio.fixture
async def paulo_user(seed_users: list[User]) -> User:
    """User Paulo (DIRIGENTE) — shortcut."""
    return next(u for u in seed_users if u.email == "paulo@pscode.ia.br")


@pytest_asyncio.fixture
async def manoel_user(seed_users: list[User]) -> User:
    """User Manoel (FISCAL) — shortcut."""
    return next(u for u in seed_users if u.email == "manoel@sindestiva-pe.com.br")


@pytest_asyncio.fixture
async def josias_user(seed_users: list[User]) -> User:
    """User Josias (DIRIGENTE) — shortcut."""
    return next(u for u in seed_users if u.email == "josias@sindestiva-pe.com.br")


# ---------------------------------------------------------------------------
# TPA com senha (pra testes LGPD que precisam de TPA logado)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def tpa_user_with_login(db_session: AsyncSession) -> User:
    """User com role=FISCAL e Tpa vinculado (pra testes de LGPD).

    O `auth/login` exige password_hash. A constraint
    `ck_users_password_for_non_tpa` proíbe password_hash em users
    com role='TPA'. Logo, criamos um user role='FISCAL' (que pode ter
    senha) E um Tpa linked a ele — o endpoint LGPD busca TPA por
    `tpa.user_id = ?`, sem checar role do user.

    Idempotente: se já existe (cleanup pode ter deixado), atualiza.
    """
    from sqlalchemy import select  # noqa: PLC0415

    from app.models import Funcao, Porto, Tpa, Turno  # noqa: PLC0415
    from app.models.enums import TpaStatusEnum  # noqa: PLC0415

    tpa_email = "tpa-login@sindestiva-test.com.br"

    # 1) User com password (role=FISCAL pra escapar constraint).
    stmt = select(User).where(User.email == tpa_email)
    user = (await db_session.execute(stmt)).scalar_one_or_none()
    if user is None:
        user = User(
            email=tpa_email,
            telefone="+5581999990099",
            password_hash=hash_password("tpa-dev-2026"),
            role=RoleEnum.FISCAL,
            status=UserStatusEnum.ATIVO,
            accepted_terms_at=datetime.now(tz=timezone.utc),
            accepted_terms_version="1.0",
        )
        db_session.add(user)
        await db_session.flush()
    else:
        user.password_hash = hash_password("tpa-dev-2026")
        user.status = UserStatusEnum.ATIVO

    # 2) Tpa linked (se já existe, atualiza). Função/Porto/Turno podem
    # ter sido deletados pelo cleanup? Não — não estão em TABLES_TO_CLEAN.
    stmt_tpa = select(Tpa).where(Tpa.user_id == user.id)
    tpa = (await db_session.execute(stmt_tpa)).scalar_one_or_none()
    if tpa is None:
        # Pega o primeiro Função/Porto/Turno do seed.
        funcao = (await db_session.execute(select(Funcao).limit(1))).scalar_one()
        porto = (await db_session.execute(select(Porto).limit(1))).scalar_one()
        turno = (await db_session.execute(select(Turno).limit(1))).scalar_one()
        tpa = Tpa(
            user_id=user.id,
            # 11 dígitos (CPF constraint). Não é válido formalmente
            # (checksum), mas passa a CHECK de formato.
            cpf=f"{secrets.randbelow(10**9):09d}00",
            nome_completo="TPA Login de Teste",
            matricula_ogmo=f"OG-TEST-{secrets.token_hex(2).upper()}"[:10],
            telefone="+5581999990099",
            funcao_base_id=funcao.id,
            categoria="Mando",
            status_cadastro=TpaStatusEnum.ATIVO,
        )
        db_session.add(tpa)
        await db_session.flush()
        # `porto_id` e `turno_id` em Tpa? Não — Tpa só tem funcao_base_id.
        # O endpoint LGPD não checa esses campos.
        # Atribuímos pra evitar warning do SQLAlchemy:
        del porto, turno  # noqa: F841

    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def api_token_tpa(
    client: httpx.AsyncClient, tpa_user_with_login: User
) -> str:
    """Login do TPA de teste na API live — retorna JWT.

    Depende de `tpa_user_with_login` pra garantir que o user existe
    no banco antes de tentar login.
    """
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "tpa-login@sindestiva-test.com.br", "password": "tpa-dev-2026"},
    )
    assert resp.status_code == 200, f"TPA login failed: {resp.text}"
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Client HTTP (integração contra API live)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Cliente HTTP contra a API live em http://127.0.0.1:8765.

    Briefng diz "API rodando, não derrube" — então apontamos pra ela.
    Os testes de integração (auth_router, lgpd) batem aqui. Os de
    unidade (auth_service, models) usam `db_session` direto, sem HTTP.
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as c:
        yield c


@pytest_asyncio.fixture
async def api_token_paulo(
    client: httpx.AsyncClient, seed_users: list[User]
) -> str:
    """Login do Paulo na API live — retorna JWT.

    Depende de `seed_users` pra garantir que o user existe.
    """
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "paulo@pscode.ia.br", "password": SEED_PASSWORD},
    )
    assert resp.status_code == 200, f"Paulo login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def api_token_manoel(
    client: httpx.AsyncClient, seed_users: list[User]
) -> str:
    """Login do Manoel (FISCAL) na API live.

    Depende de `seed_users` pra garantir que o user existe.
    """
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "manoel@sindestiva-pe.com.br", "password": SEED_PASSWORD},
    )
    assert resp.status_code == 200, f"Manoel login failed: {resp.text}"
    return resp.json()["access_token"]
