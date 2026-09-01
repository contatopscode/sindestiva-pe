"""Sanity test do conftest — não conta na entrega, só pra validar fixtures."""
import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_limpa_lgpd(db_session):
    result = await db_session.execute(text("SELECT current_schema()"))
    schema = result.scalar()
    assert schema == "lousa_main"
    # termos_consentimento deve estar vazio após cleanup
    result = await db_session.execute(
        text("SELECT count(*) FROM lousa_main.termos_consentimento")
    )
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_seed_users_ok(seed_users):
    assert len(seed_users) == 3
    emails = {u.email for u in seed_users}
    assert "paulo@pscode.ia.br" in emails
    assert "manoel@sindestiva-pe.com.br" in emails
    assert "josias@sindestiva-pe.com.br" in emails
