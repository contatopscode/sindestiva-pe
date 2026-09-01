"""SINDESTIVA-PE · Auth service (Sprint 1 T1-08).

Implementação real do login:
- Recebe `email` + `password`
- Busca `User` por email (citext)
- Verifica `password_hash` via bcrypt
- Atualiza `last_login_at`, `last_login_ip`, `last_login_user_agent`
- Reseta `failed_login_count` se sucesso
- Bloqueia se `failed_login_count >= 5` por 15min (`blocked_until`)
- Devolve JWT com `sub` (user_id) + `role` + `fiscal_id` (se fiscal)

DD v1 §3.1: User tem `password_hash` nullable (TPA pode não ter).
A constraint `ck_users_password_for_non_tpa` (na migration 0001) já
garante que TPA nunca tem senha. Se um TPA tentar logar, retorna 401
genérico (não vaza "TPA não tem senha").

Pega-dica (cross-projeto, MEMORY): NUNCA usar `asyncio.run()` dentro
de lifespan FastAPI. Aqui não há lifespan, mas o AsyncSession já
vem injetado via `Depends(get_db)`, sem nunca instanciar engine.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Fiscal, User

log = get_logger(__name__)

# Constantes de bloqueio (DD v1 §3.1 + plano T1-08).
MAX_FAILED_LOGINS = 5
BLOCK_DURATION_MINUTES = 15


class AuthError(Exception):
    """Erro de auth. Mensagem SEMPRE genérica (não vaza qual campo falhou)."""

    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


async def authenticate(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, str]:
    """Autentica user. Retorna (User, JWT).

    Raises:
        AuthError: 401 (credenciais inválidas, conta bloqueada, etc).
    """
    # 1. Busca user por email (citext é case-insensitive nativo)
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user: User | None = result.scalar_one_or_none()

    # 2. Se não existe, ou senha não bate, OU TPA sem senha, falha genérica
    if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
        # Incrementa failed_login_count se user existe (não vaza se existe)
        if user is not None:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= MAX_FAILED_LOGINS:
                user.blocked_until = datetime.now(tz=timezone.utc).replace(
                    tzinfo=None
                ) + (  # remover tz pra bater com DateTime(timezone=False) ?
                    # Na verdade o column é DateTime(timezone=True) — manter tz.
                    __import__("datetime").timedelta(minutes=BLOCK_DURATION_MINUTES)
                )
                log.warning("auth.blocked", user_id=str(user.id), count=user.failed_login_count)
            await db.commit()
        log.info("auth.failed", email=email, ip=ip)
        raise AuthError(401, "INVALID_CREDENTIALS", "Email ou senha inválidos.")

    # 3. Verifica se conta está bloqueada
    if user.blocked_until and user.blocked_until > datetime.now(tz=timezone.utc):
        log.warning("auth.blocked_attempt", user_id=str(user.id))
        raise AuthError(423, "ACCOUNT_BLOCKED", "Conta bloqueada por excesso de tentativas. Tente novamente em 15 min.")

    # 4. Verifica status
    if user.status.value in ("BLOQUEADO", "INATIVO"):
        log.warning("auth.inactive", user_id=str(user.id), status=user.status.value)
        raise AuthError(403, "ACCOUNT_DISABLED", f"Conta {user.status.value.lower()}.")

    # 5. Sucesso — atualiza last_login, reseta failed_login_count
    now = datetime.now(tz=timezone.utc)
    user.last_login_at = now
    if ip:
        user.last_login_ip = ip
    if user_agent:
        user.last_login_user_agent = user_agent
    user.failed_login_count = 0
    user.blocked_until = None
    await db.commit()
    await db.refresh(user)

    # 6. Cria JWT com claims extras (role + fiscal_id se fiscal)
    extra_claims: dict[str, Any] = {"role": user.role.value}
    if user.fiscal and user.fiscal.id:
        extra_claims["fiscal_id"] = str(user.fiscal.id)
    token = create_access_token(subject=str(user.id), extra_claims=extra_claims)

    log.info("auth.success", user_id=str(user.id), role=user.role.value, ip=ip)
    return user, token


async def ensure_user_with_password(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    role: str,
    telefone: str | None = None,
    status: str = "ATIVO",
) -> User:
    """Cria ou atualiza user com senha. Útil pro seed de Paulo/Manoel/Josias.

    Se user já existe (por email), atualiza password_hash + status.
    Caso contrário, cria.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        from app.models.enums import RoleEnum, UserStatusEnum
        user = User(
            email=email,
            telefone=telefone,
            password_hash=hash_password(password),
            role=RoleEnum(role),
            status=UserStatusEnum(status),
            accepted_terms_at=datetime.now(tz=timezone.utc),
            accepted_terms_version="1.0",
        )
        db.add(user)
    else:
        user.password_hash = hash_password(password)
        user.status = status
    await db.commit()
    await db.refresh(user)
    return user


async def get_fiscal_id_for_user(db: AsyncSession, user_id: str) -> str | None:
    """Retorna fiscal_id se user for fiscal. Helper pra JWT claims."""
    stmt = select(Fiscal).where(Fiscal.user_id == user_id)
    result = await db.execute(stmt)
    fiscal = result.scalar_one_or_none()
    return str(fiscal.id) if fiscal else None


__all__ = [
    "AuthError",
    "authenticate",
    "ensure_user_with_password",
    "get_fiscal_id_for_user",
    "MAX_FAILED_LOGINS",
    "BLOCK_DURATION_MINUTES",
]
