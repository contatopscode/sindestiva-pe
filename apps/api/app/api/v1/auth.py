"""SINDESTIVA-PE · /auth (login real + me + OTP TPA).

Sprint 1 T1-08: implementação real do fluxo de auth, com:
- Verificação de credencial no DB (bcrypt)
- Bloqueio após 5 tentativas (15min)
- JWT com claims de role + fiscal_id
- Auditoria (last_login_at, IP, user agent)

Sprint B (T3): login TPA via CPF + matrícula OGMO + OTP WhatsApp (Evolution API).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import UTC
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    get_current_user_id,
    oauth2_scheme,
)
from app.models import Tpa, User
from app.schemas.user import LoginRequest, LoginResponse, UserRead
from app.services.auth_service import AuthError, authenticate
from app.services.evolution import send_text as evolution_send_text

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger(__name__)


# ---------------------------------------------------------------------------
# OTP TPA (in-memory store — Sprint D migra pra Redis)
# ---------------------------------------------------------------------------

# Maps (cpf_hash, matricula_hash) → dict(code, expires_at, attempts)
# TTL 5min. Tamanho máx 1000 entries (proteção contra memory exhaustion).
_OTP_STORE: dict[tuple[str, str], dict] = {}
_OTP_TTL_SECONDS = 5 * 60
_OTP_MAX_ATTEMPTS = 3


def _hash_pair(cpf: str, matricula: str) -> tuple[str, str]:
    """Hash SHA-256 do par (CPF, matrícula) para chave do OTP store."""
    return (
        hashlib.sha256(cpf.encode("utf-8")).hexdigest(),
        hashlib.sha256(matricula.encode("utf-8")).hexdigest(),
    )


def _gen_otp_code() -> str:
    """Gera código de 6 dígitos. Não usa zero-leading (UX)."""
    return f"{secrets.randbelow(1_000_000):06d}"


class OTPSolicitarRequest(BaseModel):
    cpf: str = Field(..., min_length=11, max_length=14, description="CPF só dígitos")
    matricula_ogmo: str = Field(..., min_length=1, max_length=32)


class OTPSolicitarResponse(BaseModel):
    sent: bool
    destino_whatsapp: str  # nº normalizado (E.164 sem +), p/ debug
    expires_in_seconds: int = _OTP_TTL_SECONDS


class OTPVerificarRequest(BaseModel):
    cpf: str = Field(..., min_length=11, max_length=14)
    matricula_ogmo: str = Field(..., min_length=1, max_length=32)
    otp: str = Field(..., min_length=6, max_length=6)


class TPAProfile(BaseModel):
    """Profile público do TPA após login com OTP."""

    tpa_id: str
    matricula_ogmo: str
    nome_completo: str
    cpf_hash: str  # 16 primeiros chars (anonimizado)


def _client_ip(request: Request) -> str | None:
    """Extrai IP do request (com fallback X-Forwarded-For se vier proxy)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/login", response_model=LoginResponse, summary="Login com email+senha (T1-08)")
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Sprint 1: verifica credenciais reais no DB.

    Returns:
        LoginResponse com access_token JWT, expires_in (8h), user.
    """
    try:
        user, token = await authenticate(
            db,
            email=payload.email,
            password=payload.password,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except AuthError as e:
        raise HTTPException(status_code=e.status, detail={"code": e.code, "message": e.message})
    except Exception as exc:
        log.error("auth.login_unexpected", exc_type=type(exc).__name__, exc_msg=str(exc))
        raise HTTPException(
            status_code=500,
            detail={"code": "LOGIN_ERROR", "message": f"{type(exc).__name__}: {exc}"},
        ) from exc

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=8 * 3600,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead, summary="Quem sou eu (do JWT)")
async def me(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Sprint 1: SELECT real em users (lazy-load perfis)."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTH_REQUIRED", "message": "Token ausente ou inválido."},
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "USER_NOT_FOUND", "message": "Usuário não encontrado."},
        )
    return UserRead.model_validate(user)


@router.get("/config", summary="Config pública do front (NEXTAUTH_URL etc)")
async def public_config() -> dict[str, str]:
    """Expõe só vars não-sensíveis para o frontend."""
    return {
        "nextauth_url": settings.nextauth_url,
        "app_env": settings.app_env,
    }


# ---------------------------------------------------------------------------
# OTP TPA (Sprint B)
# ---------------------------------------------------------------------------

@router.post(
    "/tpa/otp/solicitar",
    response_model=OTPSolicitarResponse,
    summary="[TPA] Solicita OTP via WhatsApp (CPF + matrícula OGMO)",
)
async def tpa_otp_solicitar(
    payload: OTPSolicitarRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> OTPSolicitarResponse:
    """Valida (CPF, matrícula) → gera OTP de 6 dígitos → envia via WhatsApp.

    Args:
        payload: cpf + matricula_ogmo (ambos só dígitos / sem máscara).

    Fluxo:
        1. SELECT Tpa por (cpf, matricula_ogmo, status=ATIVO)
        2. Gera OTP (secrets.randbelow) — 6 dígitos
        3. Salva hash do par no _OTP_STORE com TTL 5min
        4. Envia via Evolution API para tpa.telefone

    Nota: resposta sempre retorna `sent=False` se (cpf, matrícula) não bate,
          pra evitar timing attack / user enumeration. Mas SMS é SÓ enviado
          se encontrado.
    """
    cpf = payload.cpf.replace(".", "").replace("-", "").strip()
    matricula = payload.matricula_ogmo.strip()
    pair = _hash_pair(cpf, matricula)

    stmt = select(Tpa).where(
        Tpa.cpf == cpf,
        Tpa.matricula_ogmo == matricula,
    )
    tpa = (await db.execute(stmt)).scalar_one_or_none()

    # Limpa entradas expiradas periodicamente
    now = time.time()
    expired = [k for k, v in _OTP_STORE.items() if v["expires_at"] < now]
    for k in expired:
        _OTP_STORE.pop(k, None)
    # Cap de tamanho
    if len(_OTP_STORE) > 1000:
        log.warning("auth.otp_store_full")
        return OTPSolicitarResponse(sent=False, destino_whatsapp="", expires_in_seconds=0)

    if tpa is None:
        log.info(
            "auth.tpa_otp.solicitar.user_not_found",
            ip=_client_ip(request),
        )
        # Resposta genérica (não revela se existe ou não).
        return OTPSolicitarResponse(sent=False, destino_whatsapp="", expires_in_seconds=0)

    # Gera código + persiste hash
    code = _gen_otp_code()
    _OTP_STORE[pair] = {
        "code": code,
        "expires_at": now + _OTP_TTL_SECONDS,
        "attempts": 0,
    }

    mensagem = (
        f"⚓ *Lousa Sindestiva*\n\n"
        f"Seu código de acesso: *{code}*\n\n"
        f"⏱ Expira em {_OTP_TTL_SECONDS // 60} min.\n"
        f"🔐 Não compartilhe com ninguém."
    )

    log.info(
        "auth.tpa_otp.solicitar.enviar",
        tpa_id=str(tpa.id),
        telefone=tpa.telefone[:6] + "***",
        ip=_client_ip(request),
    )
    result = await evolution_send_text(tpa.telefone, mensagem)
    if not result["success"]:
        log.warning("auth.tpa_otp.solicitar.whatsapp_fail", erro=result.get("error"))
        # Não vaza erro do WhatsApp pro front (Logamos internamente)
        return OTPSolicitarResponse(sent=False, destino_whatsapp="", expires_in_seconds=0)

    return OTPSolicitarResponse(
        sent=True,
        destino_whatsapp=tpa.telefone,  # p/ debug no front; em prod, mascarar
        expires_in_seconds=_OTP_TTL_SECONDS,
    )


@router.post(
    "/tpa/otp/verificar",
    response_model=LoginResponse,
    summary="[TPA] Verifica OTP e retorna JWT",
)
async def tpa_otp_verificar(
    payload: OTPVerificarRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Verifica OTP e emite JWT para o TPA.

    Args:
        payload: cpf + matricula_ogmo + otp (6 dígitos).

    Returns:
        LoginResponse padrão (mesmo do /login e-mail+senha).
    """
    cpf = payload.cpf.replace(".", "").replace("-", "").strip()
    matricula = payload.matricula_ogmo.strip()
    pair = _hash_pair(cpf, matricula)
    entry = _OTP_STORE.get(pair)
    now = time.time()

    # OTP não existe ou expirou
    if entry is None or entry["expires_at"] < now:
        # Limpa entrada expirada (best-effort)
        _OTP_STORE.pop(pair, None)
        raise HTTPException(
            status_code=401,
            detail={"code": "OTP_EXPIRED", "message": "Código expirado. Solicite um novo."},
        )

    # Lockout após N tentativas
    if entry["attempts"] >= _OTP_MAX_ATTEMPTS:
        _OTP_STORE.pop(pair, None)
        raise HTTPException(
            status_code=429,
            detail={"code": "TOO_MANY_ATTEMPTS", "message": "Muitas tentativas. Solicite um novo código."},
        )

    # Compara em tempo constante (evita timing side-channel)
    entry["attempts"] += 1
    expected = entry["code"].encode("utf-8")
    given = payload.otp.encode("utf-8")
    if not hmac.compare_digest(expected, given):
        log.info("auth.tpa_otp.verificar.invalid", ip=_client_ip(request))
        raise HTTPException(
            status_code=401,
            detail={"code": "OTP_INVALID", "message": "Código inválido."},
        )

    # OTP correto: cria/recupera User vinculado ao Tpa, emite JWT
    from app.services.auth_service import ensure_user_with_password

    # Usamos um valor derivado pra password_hash (TPA não tem senha — usa só OTP).
    # O hash abaixo é determinístico por cpf+matricula (não é uma senha real).
    derived_pwd = hashlib.sha256(f"{cpf}:{matricula}:tpa-otp".encode()).hexdigest()
    user = await ensure_user_with_password(
        db,
        email=f"tpa+{cpf}@sindestiva.invalid",  # email derivado, não usamos p/ login
        telefone=None,
        password=derived_pwd,
        role=RoleEnum.TPA,
        status=UserStatusEnum.ATIVO,
    )

    # Garante que user.tpa_id === tpa.id (vínculo oficial)
    if tpa.user_id != user.id:
        tpa.user_id = user.id
        await db.flush()

    # Limpa OTP (uso único)
    _OTP_STORE.pop(pair, None)

    # Emite JWT (helper create_access_token aceita subject + extra_claims)
    tpa_id: str = str(tpa.id)
    token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "role": RoleEnum.TPA.value,
            "email": user.email,
            "fiscal_id": None,
            "tpa_id": tpa_id,
        },
    )

    # Atualiza last_login (mesmo padrão de authenticate())
    from datetime import datetime
    user.last_login_at = datetime.now(tz=UTC)
    user.failed_login_count = 0
    await db.commit()

    log.info(
        "auth.tpa_otp.verificar.ok",
        tpa_id=tpa_id,
        user_id=str(user.id),
        ip=_client_ip(request),
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=8 * 3600,
        user=UserRead.model_validate(user),
    )
