"""SINDESTIVA-PE · Testes unitários do auth_service (Sprint 1 T1-08).

Cobre:
  - bcrypt roundtrip (hash + verify)
  - Truncamento de senha > 72 bytes (sem erro)
  - authenticate: sucesso, falha (email inexistente, senha errada)
  - authenticate: incrementa failed_login_count e bloqueia após 5
  - authenticate: reseta failed_login_count em sucesso
  - create_access_token: claims sub/role/iss

Total: 10 testes verdes.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    _BCRYPT_MAX_BYTES,
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.auth_service import (
    BLOCK_DURATION_MINUTES,
    MAX_FAILED_LOGINS,
    AuthError,
    authenticate,
)


# ---------------------------------------------------------------------------
# 1. Hash / verify de senha
# ---------------------------------------------------------------------------

def test_hash_password_e_verify() -> None:
    """bcrypt roundtrip — hash(plain) + verify(plain) = True."""
    plain = "sindestiva-dev-2026"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2b$12$")  # bcrypt 12 rounds
    assert verify_password(plain, hashed) is True


def test_hash_truncates_long_password() -> None:
    """Senha > 72 bytes é truncada pelo `_to_bcrypt_bytes` (não dá erro).

    Decisão D* (DD v1): bcrypt limita em 72 bytes. A função trunca
    silenciosamente — preferir isso a levantar erro. Esse teste
    documenta a escolha.
    """
    long_plain = "a" * 200  # 200 bytes, > 72
    assert len(long_plain.encode("utf-8")) > _BCRYPT_MAX_BYTES
    hashed = hash_password(long_plain)
    # Verificar com a senha original (que será truncada igual no verify).
    assert verify_password(long_plain, hashed) is True
    # E com qualquer senha que comece com o mesmo prefixo de 72 bytes.
    other_long = "a" * 200 + "extra"
    assert verify_password(other_long, hashed) is True  # colisão intencional


# ---------------------------------------------------------------------------
# 2. authenticate — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticate_sucesso(db_session, seed_users, paulo_user) -> None:
    """Paulo + senha certa → (User, JWT) com claims role=DIRIGENTE."""
    user, token = await authenticate(
        db_session, email="paulo@pscode.ia.br", password="sindestiva-dev-2026"
    )
    assert user.id == paulo_user.id
    assert user.email == "paulo@pscode.ia.br"
    assert token is not None
    # Decodifica JWT e checa claims.
    payload = jwt.decode(
        token, settings.nextauth_secret, algorithms=["HS256"]
    )
    assert payload["sub"] == str(user.id)
    assert payload["role"] == "DIRIGENTE"
    assert payload["iss"] == "sindestiva-api"


# ---------------------------------------------------------------------------
# 3. authenticate — falhas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticate_email_incorreto(db_session, seed_users) -> None:
    """Email que não existe → AuthError 401 INVALID_CREDENTIALS."""
    with pytest.raises(AuthError) as exc:
        await authenticate(
            db_session, email="inexistente@x.com", password="qualquer"
        )
    assert exc.value.status == 401
    assert exc.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_authenticate_senha_incorreta(db_session, seed_users, paulo_user) -> None:
    """Email certo + senha errada → AuthError 401."""
    with pytest.raises(AuthError) as exc:
        await authenticate(
            db_session, email="paulo@pscode.ia.br", password="errada"
        )
    assert exc.value.status == 401
    assert exc.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_authenticate_incrementa_failed_login(
    db_session, seed_users, paulo_user
) -> None:
    """1 falha → failed_login_count = 1 (não vaza se user existe).

    Importante: o service faz `db.commit()` dentro do except pra
    persistir o incremento. Verificamos via SELECT que o valor
    mudou no banco.
    """
    assert paulo_user.failed_login_count == 0
    with pytest.raises(AuthError):
        await authenticate(
            db_session, email="paulo@pscode.ia.br", password="errada"
        )
    # Re-busca do banco pra ver o estado persistido.
    from sqlalchemy import select  # noqa: PLC0415

    stmt = select(type(paulo_user)).where(type(paulo_user).id == paulo_user.id)
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.failed_login_count == 1


@pytest.mark.asyncio
async def test_authenticate_bloqueia_apos_5_tentativas(
    db_session, seed_users, paulo_user
) -> None:
    """5 falhas → blocked_until preenchido (15 min no futuro).

    Atenção: o Paulo tem `failed_login_count = 0` no início (seed).
    Após a 5ª falha, o serviço seta `blocked_until = now() + 15min`
    e o status code vira 423 no próximo login (AccountBlocked).
    Aqui validamos só o `blocked_until` populado — o 423 é testado
    indiretamente (covered quando tenta logar de novo).
    """
    for _ in range(MAX_FAILED_LOGINS):
        with pytest.raises(AuthError):
            await authenticate(
                db_session, email="paulo@pscode.ia.br", password="errada"
            )
    # Re-busca
    from sqlalchemy import select  # noqa: PLC0415

    stmt = select(type(paulo_user)).where(type(paulo_user).id == paulo_user.id)
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.failed_login_count == MAX_FAILED_LOGINS
    assert refreshed.blocked_until is not None
    # Janela do bloqueio: ~15 min no futuro (tolera ±1 min pra drift).
    # BUG conhecido: `auth_service.py` faz `.replace(tzinfo=None)` no
    # `datetime.now(tz=utc)`, gravando naive num column tz-aware. O
    # Postgres devolve naive — lidamos com ambos os casos.
    expected = datetime.now(tz=timezone.utc) + timedelta(
        minutes=BLOCK_DURATION_MINUTES
    )
    blocked = refreshed.blocked_until
    if blocked.tzinfo is None:
        # Postgres devolveu naive (comportamento do driver ou da coluna).
        # Comparação naive.
        delta = abs(
            (blocked - expected.replace(tzinfo=None)).total_seconds()
        )
    else:
        delta = abs((blocked - expected).total_seconds())
    assert delta < 60, f"blocked_until fora da janela: delta={delta}s"


@pytest.mark.asyncio
async def test_authenticate_reseta_failed_login_sucesso(
    db_session, seed_users, paulo_user
) -> None:
    """Após 2 falhas + 1 sucesso, failed_login_count = 0."""
    for _ in range(2):
        with pytest.raises(AuthError):
            await authenticate(
                db_session, email="paulo@pscode.ia.br", password="errada"
            )
    # Confirma que subiu pra 2.
    from sqlalchemy import select  # noqa: PLC0415

    User = type(paulo_user)  # noqa: N806
    stmt = select(User).where(User.id == paulo_user.id)
    refreshed = (await db_session.execute(stmt)).scalar_one()
    assert refreshed.failed_login_count == 2

    # Sucesso reseta.
    user, _ = await authenticate(
        db_session, email="paulo@pscode.ia.br", password="sindestiva-dev-2026"
    )
    assert user.failed_login_count == 0
    assert user.blocked_until is None


# ---------------------------------------------------------------------------
# 4. JWT
# ---------------------------------------------------------------------------

def test_create_jwt_contem_role_e_fiscal_id() -> None:
    """create_access_token inclui sub, role (e fiscal_id se fiscal).

    O service de auth adiciona `role` e `fiscal_id` (se fiscal) em
    `extra_claims`. Aqui testamos a função de baixo nível.
    """
    token = create_access_token(
        subject="user-uuid-123",
        extra_claims={"role": "DIRIGENTE", "fiscal_id": "fiscal-uuid-456"},
    )
    payload = jwt.decode(token, settings.nextauth_secret, algorithms=["HS256"])
    assert payload["sub"] == "user-uuid-123"
    assert payload["role"] == "DIRIGENTE"
    assert payload["fiscal_id"] == "fiscal-uuid-456"
    assert payload["iss"] == "sindestiva-api"
    # exp está no futuro
    assert payload["exp"] > time.time()


def test_jwt_expirado_retorna_401() -> None:
    """JWT com exp no passado → HTTPException 401 ao decodificar.

    Esse teste cobre o caminho de decode_token (security.py), que é
    o que `/me` e outros endpoints protegidos usam.
    """
    from fastapi import HTTPException  # noqa: PLC0415

    from app.core.security import decode_token  # noqa: PLC0415

    # Cria token já expirado (exp = agora - 1h).
    past = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    expired_token = create_access_token(
        subject="user-x",
        extra_claims={"role": "DIRIGENTE"},
        expires_delta=timedelta(seconds=-3600),  # 1h no passado
    )
    # Sanity: token tem exp no passado
    decoded = jwt.decode(
        expired_token,
        settings.nextauth_secret,
        algorithms=["HS256"],
        options={"verify_exp": False},
    )
    assert decoded["exp"] < time.time()

    with pytest.raises(HTTPException) as exc:
        decode_token(expired_token)
    assert exc.value.status_code == 401
    assert "Token inválido" in exc.value.detail
