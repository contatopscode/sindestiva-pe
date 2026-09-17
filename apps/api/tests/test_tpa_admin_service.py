"""Unit tests — tpa_admin_service helpers (FSW-2026-008)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models import Funcao
from app.services.tpa_admin_service import _load_funcoes_by_ids


def _funcao_stub(*, ordem: int) -> Funcao:
    fid = uuid4()
    return Funcao(
        id=fid,
        codigo=f"COD_{ordem}",
        nome_exibicao=f"Função {ordem}",
        categoria="TECNICA",
        ordem_lousa=ordem,
        is_active=True,
        created_at=datetime.now(tz=UTC),
    )


@pytest.mark.asyncio
async def test_load_funcoes_by_ids_returns_funcao_objects_ordered() -> None:
    """Regression: must return Funcao rows, not UUIDs (used by _resolve_funcao_write)."""
    f_low = _funcao_stub(ordem=5)
    f_high = _funcao_stub(ordem=15)
    # Request order inverted; response should follow ordem_lousa.
    request_ids = [f_high.id, f_low.id]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [f_high, f_low]

    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    loaded = await _load_funcoes_by_ids(db, request_ids)

    assert len(loaded) == 2
    assert all(isinstance(row, Funcao) for row in loaded)
    assert [row.id for row in loaded] == [f_low.id, f_high.id]
    assert loaded[0].ordem_lousa < loaded[1].ordem_lousa
