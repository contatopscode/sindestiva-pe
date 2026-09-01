"""SINDESTIVA-PE · Testes de integração do /auth (Sprint 1 T1-08).

Cobre o router FastAPI contra a API live (`http://127.0.0.1:8765`):
  - POST /api/v1/auth/login (sucesso e senha errada)
  - GET /api/v1/auth/me (com token, sem token, token inválido)
  - GET /api/v1/health (db=ok)

Total: 6 testes verdes.

Pré-requisito: a API deve estar rodando (briefing). Os testes NÃO
derrubam nem reiniciam a API.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 1. Login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_sucesso_retorna_jwt_e_user(client) -> None:
    """POST /auth/login com credenciais válidas → 200 + access_token + user."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "paulo@pscode.ia.br", "password": "sindestiva-dev-2026"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 8 * 3600
    assert body["user"]["email"] == "paulo@pscode.ia.br"
    assert body["user"]["role"] == "DIRIGENTE"
    assert body["user"]["status"] == "ATIVO"


@pytest.mark.asyncio
async def test_login_senha_errada_retorna_401(client) -> None:
    """POST /auth/login com senha errada → 401 + code INVALID_CREDENTIALS."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "paulo@pscode.ia.br", "password": "errada"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# 2. /me — dependência do token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_me_com_token_valido(client, api_token_paulo) -> None:
    """GET /me com Bearer token válido → 200 + dados do Paulo."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "paulo@pscode.ia.br"
    assert body["role"] == "DIRIGENTE"


@pytest.mark.asyncio
async def test_me_sem_token_retorna_401(client) -> None:
    """GET /me sem header Authorization → 401 + code AUTH_REQUIRED."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_me_com_token_invalido_retorna_401(client) -> None:
    """GET /me com "Bearer lixo" → 401 (JWT inválido / não decodifica)."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer lixo.invalido.token"},
    )
    assert resp.status_code == 401
    # Pode ser AUTH_REQUIRED (decode falhou) ou detalhe genérico.
    # O importante: status 401 e NÃO 200.
    assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# 3. Health (db ping)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint(client) -> None:
    """GET /api/v1/health → 200 + db=ok (lousa_main.users existe)."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["service"] == "sindestiva-api"
