"""SINDESTIVA-PE · Segurança (hash de senha, JWT, dependências de auth).

Stack: bcrypt 4.x direto (passlib tem bug com bcrypt 4.x em detect_wrap_bug) +
       python-jose para JWT. NextAuth v5 (Sprint 1 T1-04) é o issuer
       primário no frontend; este módulo valida tokens emitidos por lá.

Decisão D1 (DD v1): TPA pode ter `password_hash`? Recomendação
SINDESTIVA Bot = (a) só OTP. A constraint `ck_users_password_for_non_tpa`
foi incluída no DD mas pode ser removida se o Paulo confirmar D1.

Pega-dica (cross-projeto, MEMORY): passlib 1.7.4 + bcrypt 4.x tem bug
no `detect_wrap_bug` (testa senha > 72 bytes que bcrypt não aceita).
Solução: usar `bcrypt` direto (não passlib). Funciona em Docker Alpine
e no Mac M1. Argon2id preferido em prod (DD v1 menciona) — trocar
no Sprint 8 quando auditarmos segurança.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings

# NextAuth v5 emite JWT com `alg: HS256` e `NEXTAUTH_SECRET`. Em S1
# validamos esse token no backend; em produção migrar para RS256 com
# JWKS.
JWT_ALGORITHM = "HS256"

# OAuth2PasswordBearer só define o esquema (Authorization: Bearer ...).
# O tokenUrl é só metadata do OpenAPI — login real vem do NextAuth no
# frontend.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Bcrypt tem limite de 72 bytes na senha. Truncar manualmente (docs oficiais).
_BCRYPT_MAX_BYTES = 72


# ---------------------------------------------------------------------------
# Hash / verificação de senha
# ---------------------------------------------------------------------------

def _to_bcrypt_bytes(plain: str) -> bytes:
    """Converte senha pra bytes, truncada em 72 bytes se necessário."""
    raw = plain.encode("utf-8")
    return raw[:_BCRYPT_MAX_BYTES] if len(raw) > _BCRYPT_MAX_BYTES else raw


def hash_password(plain: str) -> str:
    """Gera hash bcrypt (12 rounds) da senha em texto plano."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(_to_bcrypt_bytes(plain), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica senha em texto plano contra hash bcrypt."""
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(
    *,
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Cria JWT assinado com `NEXTAUTH_SECRET`.

    `subject` é o identificador do user (uuid str). `extra_claims` vai
    inteiro pro payload (ex: role, fiscal_id).
    """
    if not settings.nextauth_secret:
        raise RuntimeError(
            "NEXTAUTH_SECRET não configurado. Rode `openssl rand -base64 32` e preencha o .env"
        )
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(hours=8)
    )
    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(tz=timezone.utc),
        "iss": "sindestiva-api",
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.nextauth_secret, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decodifica e valida JWT. Levanta HTTPException 401 se inválido."""
    if not settings.nextauth_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth não configurado (NEXTAUTH_SECRET ausente).",
        )
    try:
        return jwt.decode(
            token,
            settings.nextauth_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc!s}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# Dependências de auth (Sprint 1 T1-08)
# ---------------------------------------------------------------------------

def get_current_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str | None:
    """Extrai `sub` (user_id) do JWT. Retorna None se token ausente.

    Sprint 1: retorna só o id; o caller faz SELECT real no DB.
    """
    if token is None:
        return None
    payload = decode_token(token)
    sub: str | None = payload.get("sub")
    return sub


def require_user(
    user_id: Annotated[str | None, Depends(get_current_user_id)],
) -> str:
    """Dependency que exige user autenticado. Levanta 401 caso contrário."""
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "get_current_user_id",
    "require_user",
    "oauth2_scheme",
]
