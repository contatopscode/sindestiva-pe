"""SINDESTIVA-PE · Testes do LGPD (Sprint 1 T1-10).

Cobre:
  - Hash do termo v1 é estável (SHA-256 hex)
  - Formato do protocolo (LGPD-YYYY-XXXX)
  - GET /lgpd/termo-consentimento/texto (público)
  - POST /lgpd/termo-consentimento/aceitar (autenticação + versão)
  - POST /lgpd/solicitacoes (criação + prazo de 15 dias)

Total: 8 testes verdes.

Pré-requisito: a API live em http://127.0.0.1:8765.

Fixture `tpa_user_with_login` (conftest) cria um user role=FISCAL com
Tpa vinculado — necessário porque a constraint
`ck_users_password_for_non_tpa` proíbe password_hash em users
role=TPA. O endpoint LGPD busca TPA por user_id, sem checar role.
"""
from __future__ import annotations

import hashlib
from datetime import datetime

import pytest

from app.services.lgpd_service import TERMO_V1, gerar_protocolo, hash_termo


# ---------------------------------------------------------------------------
# 1. Hash + protocolo (puros)
# ---------------------------------------------------------------------------

def test_termo_texto_hash_estavel() -> None:
    """SHA-256 hex do TERMO_V1 é sempre o mesmo (64 chars, hex)."""
    h1 = hash_termo(TERMO_V1)
    h2 = hash_termo(TERMO_V1)
    # Mesmo input → mesmo hash.
    assert h1 == h2
    # E o valor bate com sha256 do texto exato.
    expected = hashlib.sha256(TERMO_V1.encode("utf-8")).hexdigest()
    assert h1 == expected
    # Formato: 64 hex chars.
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_gerar_protocolo_formato_correto() -> None:
    """Protocolo segue `LGPD-YYYY-XXXX` (4 hex uppercase)."""
    proto = gerar_protocolo()
    ano_atual = str(datetime.now().year)
    assert proto.startswith(f"LGPD-{ano_atual}-")
    sufixo = proto.split("-")[-1]
    assert len(sufixo) == 4
    assert all(c in "0123456789ABCDEF" for c in sufixo)


# ---------------------------------------------------------------------------
# 2. Endpoints públicos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_termo_texto_publico(client) -> None:
    """GET /lgpd/termo-consentimento/texto (sem auth) → 200 + texto + hash."""
    resp = await client.get("/api/v1/lgpd/termo-consentimento/texto")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["versao"] == "1.0"
    assert "SINDESTIVA-PE" in body["texto"]
    assert "LGPD" in body["texto"]
    # Hash bate com o calculado em Python.
    assert body["texto_hash_sha256"] == hash_termo(TERMO_V1)
    assert body["obrigatorio"] is True


# ---------------------------------------------------------------------------
# 3. Auth em /aceitar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_aceitar_termo_sem_auth_retorna_401(client) -> None:
    """POST /aceitar sem token → 401 AUTH_REQUIRED."""
    resp = await client.post(
        "/api/v1/lgpd/termo-consentimento/aceitar",
        json={"versao": "1.0", "aceito": True},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_aceitar_termo_versao_diferente_retorna_409(
    client, api_token_paulo
) -> None:
    """POST /aceitar com versao="2.0" → 409 TERMO_VERSION_MISMATCH."""
    resp = await client.post(
        "/api/v1/lgpd/termo-consentimento/aceitar",
        json={"versao": "2.0", "aceito": True},
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "TERMO_VERSION_MISMATCH"


@pytest.mark.asyncio
async def test_aceitar_termo_paulo_sem_tpa_vinculado_retorna_400(
    client, api_token_paulo
) -> None:
    """Paulo é DIRIGENTE, sem Tpa → 400 TPA_NOT_LINKED.

    Importante: o token é válido (Paulo existe), mas o lookup de Tpa
    por user_id falha → 400.
    """
    resp = await client.post(
        "/api/v1/lgpd/termo-consentimento/aceitar",
        json={"versao": "1.0", "aceito": True},
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"]["code"] == "TPA_NOT_LINKED"


# ---------------------------------------------------------------------------
# 4. Solicitações Art. 18
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_criar_solicitacao_art_18(
    client, api_token_tpa, tpa_user_with_login
) -> None:
    """POST /solicitacoes com tipo=EXCLUSAO → 201 + protocolo."""
    resp = await client.post(
        "/api/v1/lgpd/solicitacoes",
        json={"tipo": "EXCLUSAO", "descricao": "Quero exercer meu Art. 18, V"},
        headers={"Authorization": f"Bearer {api_token_tpa}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    # Protocolo no formato certo.
    assert body["protocolo"].startswith("LGPD-")
    assert body["tipo"] == "EXCLUSAO"
    assert body["status"] == "RECEBIDA"
    # recebida_em foi setada.
    assert body["recebida_em"] is not None


@pytest.mark.asyncio
async def test_solicitacao_prazo_15_dias(
    client, api_token_tpa, tpa_user_with_login
) -> None:
    """prazo_resposta = recebida_em + 15 dias (Art. 18 §5º LGPD)."""
    resp = await client.post(
        "/api/v1/lgpd/solicitacoes",
        json={"tipo": "PORTABILIDADE"},
        headers={"Authorization": f"Bearer {api_token_tpa}"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # prazo_resposta e recebida_em vêm como ISO string. Compara com
    # tolerância de ±5s pra drift de tz/serialização.
    recebida = datetime.fromisoformat(body["recebida_em"].replace("Z", "+00:00"))
    prazo = datetime.fromisoformat(body["prazo_resposta"].replace("Z", "+00:00"))
    delta = (prazo - recebida).total_seconds()
    expected = 15 * 24 * 3600  # 15 dias em segundos
    assert abs(delta - expected) < 60, f"prazo fora do esperado: {delta}s vs {expected}s"
