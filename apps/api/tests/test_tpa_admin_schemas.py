"""Unit tests — schemas admin TPA (FSW-2026-008)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.tpa_admin import AdminTpaCreate, AdminTpaUpdate


def test_create_requires_funcao_ids_or_base() -> None:
    with pytest.raises(ValidationError):
        AdminTpaCreate(
            cpf="12345678901",
            nome_completo="Sem função",
            matricula_ogmo="1",
            telefone="+5581999999999",
        )


def test_create_legacy_funcao_base_only() -> None:
    fid = uuid4()
    body = AdminTpaCreate(
        cpf="12345678901",
        nome_completo="Legado",
        matricula_ogmo="1",
        telefone="+5581999999999",
        funcao_base_id=fid,
    )
    assert body.funcao_base_id == fid


def test_update_rejects_empty_funcao_ids() -> None:
    with pytest.raises(ValidationError):
        AdminTpaUpdate(funcao_ids=[])
