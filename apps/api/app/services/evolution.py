"""SINDESTIVA-PE · Evolution API (WhatsApp) — serviço compartilhado.

Wrapper fino sobre Evolution API (https://evolution-api.com/), mesmo
padrão usado em ecommerce-becker (Suporte Gerencial). Hospedado em
`evolution-evolution-api.vcli1q.easypanel.host` (instância `Vigilia`).

Endpoints usados:
  - POST {url}/message/sendText/{instance}  → envia texto simples
  - (futuro) POST .../message/sendMedia/... → PDF/imagem

Numeração: WhatsApp usa formato E.164 sem `+` (ex: `5581999990001`).
A função `_normalize_br` adapta nºs BR (com/sem 9º dígito).
"""

from __future__ import annotations

import re

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Normalização BR
# ---------------------------------------------------------------------------


def _normalize_br(numero: str) -> str:
    """Normaliza nº BR para o formato Evolution (E.164 sem `+`).

    Aceita:
      - `81999990001` → `5581999990001` (adiciona DDI 55)
      - `5581999990001` → `5581999990001` (já tem DDI)
      - `+55 81 99999-0001` → `5581999990001`
      - `5581999990001` (com 9º dígito, celular) → mantém
      - `558133333444` (sem 9º dígito, fixo antigo) → `5581333334444` (insere 9)

    Retorna só dígitos. Levanta ValueError se vazio/inválido.
    """
    digits = re.sub(r"\D", "", numero or "")
    if not digits:
        raise ValueError("Número de WhatsApp vazio.")

    if not digits.startswith("55"):
        digits = "55" + digits

    # Se tem 12 dígitos (55 + DDD 2 + 8 = fixo), insere o 9.
    if len(digits) == 12:
        # 55 + DD (2) + 8 dígitos → inserir 9 após DDD
        digits = digits[:4] + "9" + digits[4:]

    if len(digits) != 13:
        raise ValueError(
            f"Número inválido: {numero!r} → {digits!r} (esperado 13 dígitos, ex: 5581999990001)."
        )

    return digits


# ---------------------------------------------------------------------------
# Envio
# ---------------------------------------------------------------------------


async def send_text(
    numero: str,
    texto: str,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> dict:
    """Envia mensagem de texto via WhatsApp (Evolution API).

    Args:
        numero: nº do destinatário. Aceita vários formatos BR (ver
            `_normalize_br`).
        texto: corpo da mensagem (até ~65k chars).

    Returns:
        Dict com `{success: bool, provider_id: str | None, error: str | None}`.
    """
    if not settings.evolution_api_url or not settings.evolution_api_key:
        msg = "Evolution API não configurada (EVOLUTION_API_URL/KEY ausentes)."
        log.warning("evolution.send_text.not_configured")
        return {"success": False, "provider_id": None, "error": msg}

    try:
        numero_norm = _normalize_br(numero)
    except ValueError as exc:
        return {"success": False, "provider_id": None, "error": str(exc)}

    url = f"{settings.evolution_api_url.rstrip('/')}/message/sendText/{settings.evolution_instance}"
    headers = {
        "Content-Type": "application/json",
        "apikey": settings.evolution_api_key,
    }
    body = {"number": numero_norm, "text": texto}

    t0 = __import__("time").monotonic()
    try:
        client = http_client or httpx.AsyncClient(timeout=30)
        if http_client is None:
            response = await client.post(url, headers=headers, json=body)
        else:
            response = await http_client.post(url, headers=headers, json=body)
        await client.aclose() if http_client is None else None

        duracao_ms = int((__import__("time").monotonic() - t0) * 1000)
        if not response.is_success:
            log.warning(
                "evolution.send_text.failed",
                status=response.status_code,
                body=response.text[:300],
                duracao_ms=duracao_ms,
            )
            return {
                "success": False,
                "provider_id": None,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

        result = response.json() if response.content else {}
        provider_id = (
            result.get("key", {}).get("id")
            or result.get("messageId")
            or result.get("id")
        )
        log.info(
            "evolution.send_text.ok",
            numero=numero_norm,
            provider_id=provider_id,
            duracao_ms=duracao_ms,
        )
        return {
            "success": True,
            "provider_id": str(provider_id) if provider_id else None,
            "error": None,
            "raw": result,
        }
    except Exception as exc:  # noqa: BLE001
        log.error("evolution.send_text.exception", erro=str(exc))
        return {
            "success": False,
            "provider_id": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


async def healthcheck() -> dict:
    """Verifica se Evolution API está respondendo (sem enviar msg)."""
    if not settings.evolution_api_url:
        return {"ok": False, "error": "EVOLUTION_API_URL não configurada"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{settings.evolution_api_url.rstrip('/')}/instance/connectionState/{settings.evolution_instance}",
                headers={"apikey": settings.evolution_api_key},
            )
            return {"ok": r.is_success, "status": r.status_code}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


__all__ = ["_normalize_br", "healthcheck", "send_text"]
