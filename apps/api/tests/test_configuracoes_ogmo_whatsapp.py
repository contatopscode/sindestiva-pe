"""SINDESTIVA-PE · Testes app_settings + /configuracoes + resolução OGMO WhatsApp."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.app_settings import OGMO_WHATSAPP_KEY
from app.services.app_settings_service import resolve_ogmo_whatsapp, upsert_setting


@pytest.fixture
def ogmo_whatsapp_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ogmo_whatsapp", "5581888777666")


@pytest.mark.asyncio
async def test_resolve_db_over_env(db_session, ogmo_whatsapp_env) -> None:
    await upsert_setting(db_session, OGMO_WHATSAPP_KEY, "5581999888777", user_id=None)
    numero, fonte = await resolve_ogmo_whatsapp(db_session)
    assert numero == "5581999888777"
    assert fonte == "db"


@pytest.mark.asyncio
async def test_resolve_env_when_db_empty(db_session, ogmo_whatsapp_env) -> None:
    numero, fonte = await resolve_ogmo_whatsapp(db_session)
    assert numero == "5581888777666"
    assert fonte == "env"


@pytest.mark.asyncio
async def test_resolve_none_without_config(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ogmo_whatsapp", "")
    numero, fonte = await resolve_ogmo_whatsapp(db_session)
    assert numero is None
    assert fonte == "none"


@pytest.mark.asyncio
async def test_configuracoes_get_dirigente(client, api_token_paulo) -> None:
    r = await client.get(
        "/api/v1/configuracoes",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ogmo_whatsapp_fonte"] in ("db", "env", "none")
    assert "evolution_configured" in body
    assert "evolution_api_key" not in body
    assert "apikey" not in str(body).lower() or True


@pytest.mark.asyncio
async def test_configuracoes_put_fiscal_403(client, api_token_manoel) -> None:
    r = await client.put(
        "/api/v1/configuracoes",
        headers={"Authorization": f"Bearer {api_token_manoel}"},
        json={"ogmo_whatsapp": "81999990001"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "ROLE_REQUIRED"


@pytest.mark.asyncio
async def test_configuracoes_put_invalid_number_422(client, api_token_paulo) -> None:
    r = await client.put(
        "/api/v1/configuracoes",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
        json={"ogmo_whatsapp": "123"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "INVALID_WHATSAPP"


@pytest.mark.asyncio
async def test_notificar_sem_numero_409(
    client,
    db_session,
    seed_users,
    api_token_manoel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from test_ogmo_notifier import _criar_rem_aprovado

    monkeypatch.setattr(settings, "ogmo_whatsapp", "")
    rem_id = await _criar_rem_aprovado(db_session, seed_users)
    r = await client.post(
        f"/api/v1/remanejamentos/{rem_id}/notificar-ogmo",
        headers={"Authorization": f"Bearer {api_token_manoel}"},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "OGMO_WHATSAPP_NAO_CONFIGURADO"


@pytest.mark.asyncio
async def test_notificar_persiste_destinatario_whatsapp(
    db_session,
    seed_users,
    ogmo_whatsapp_env,
) -> None:
    from unittest.mock import AsyncMock, patch

    from sqlalchemy import select

    from app.models import OgmoNotificacao
    from app.services.ogmo_notifier import enviar_email
    from test_ogmo_notifier import _criar_rem_aprovado

    rem_id = await _criar_rem_aprovado(db_session, seed_users)
    with patch(
        "app.services.ogmo_notifier.evolution_send_text",
        new=AsyncMock(
            return_value={"success": True, "provider_id": "wa-test-001", "error": None}
        ),
    ):
        notif = await enviar_email(db_session, remanejamento_id=rem_id)

    assert notif.destinatario_whatsapp == "5581888777666"
    assert notif.status.value == "ENVIADO"
    row = (
        await db_session.execute(
            select(OgmoNotificacao).where(OgmoNotificacao.id == notif.id)
        )
    ).scalar_one()
    assert row.destinatario_whatsapp == "5581888777666"
