"""SINDESTIVA-PE · Segurança (hash de senha, JWT, dependências de auth).

Stack: passlib[bcrypt] para hash de senha (T1-08 do plano) +
       python-jose para JWT. NextAuth v5 (Sprint 1 T1-04) é o issuer
       primário no frontend; este módulo valida tokens emitidos por lá.

Decisão D1 (DD v1): TPA pode ter `password_hash`? Recomendação
SINDESTIVA Bot = (a) só OTP. A constraint `ck_users_password_for_non_tpa`
foi incluída no DD mas pode ser removida se o Paulo confirmar D1.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Esquema de hash (bcrypt padrão mercado). Argon2id preferido (DD v1
# fala em Argon2id) mas bcrypt é mais portátil no Docker Alpine. Trocar
# em Sprint 0 se o Paulo pedir.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# NextAuth v5 emite JWT com `alg: HS256` e `NEXTAUTH_SECRET`. Em S1
# validamos esse token no backend; em produção migrar para RS256 com
# JWKS.
JWT_ALGORITHM = "HS256"

# OAuth2PasswordBearer só define o esquema (Authorization: Bearer ...).
# O tokenUrl é só metadata do OpenAPI — login real vem do NextAuth no
# frontend.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ---------------------------------------------------------------------------
# Hash / verificação de senha
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Gera hash bcrypt da senha em texto plano."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica senha em texto plano contra hash bcrypt."""
    return pwd_context.verify(plain, hashed)


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
# Dependências de auth (placeholders Sprint 0)
# ---------------------------------------------------------------------------

async def get_current_user_id(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str | None:
    """Extrai `sub` (user_id) do JWT. Retorna None se token ausente.

    Sprint 1 (T1-08): trocar para buscar User real no DB e retornar
    instância `User` (lazy-load). Sprint 0 retorna só o id.
    """
    if token is None:
        return None
    payload = decode_token(token)
    sub: str | None = payload.get("sub")
    return sub


async def require_user(
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
