"""SINDESTIVA-PE · /lousa/public (Sprint 0 — sem auth).

Endpoint temporário para visualização durante a Fase de Construção
(antes da Sprint 1 T1-04 implementar NextAuth + RBAC). Em produção,
**este endpoint deve ser removido** ou protegido — é só pra demo
end-to-end do Centro de Comando.

Endpoint real autenticado: `GET /api/v1/lousa/atual` (em lousa.py).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.models import Faina, Funcao, LousaCell, LousaSnapshot, Porto, Tpa, Turno
from app.models.enums import CellStatusEnum, SnapshotStatusEnum

router = APIRouter(prefix="/lousa/public", tags=["lousa-public"])
log = get_logger(__name__)


@router.get("/preview", summary="Snapshot mais recente (sem auth, Sprint 0)")
async def preview(
    porto: str = "SUAPE",
    turno: str = "DIURNO",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna snapshot + cells + catálogos (fainas, funções, TPAs) pra render.

    Sprint 0: usado pelo Centro de Comando (Next.js) durante a
    construção. Em Sprint 1+ vira `/api/v1/lousa/atual` com auth.
    """
    # Porto + turno
    stmt_p = select(Porto).where(Porto.codigo == porto)
    porto_obj = (await db.execute(stmt_p)).scalar_one_or_none()
    if porto_obj is None:
        raise HTTPException(404, f"Porto {porto} não encontrado.")

    stmt_t = select(Turno).where(Turno.codigo == turno)
    turno_obj = (await db.execute(stmt_t)).scalar_one_or_none()
    if turno_obj is None:
        raise HTTPException(404, f"Turno {turno} não encontrado.")

    # Fainas (ordenadas) e Funções (ordenadas)
    fainas = (await db.execute(
        select(Faina).where(Faina.is_active.is_(True)).order_by(Faina.ordem_lousa)
    )).scalars().all()
    funcoes = (await db.execute(
        select(Funcao).where(Funcao.is_active.is_(True)).order_by(Funcao.ordem_lousa)
    )).scalars().all()

    # Snapshot mais recente
    stmt_s = (
        select(LousaSnapshot)
        .where(LousaSnapshot.porto_id == porto_obj.id, LousaSnapshot.turno_id == turno_obj.id)
        .order_by(LousaSnapshot.scraped_at.desc())
        .limit(1)
    )
    snapshot = (await db.execute(stmt_s)).scalar_one_or_none()

    cells: list[dict] = []
    total_tpas = 0
    if snapshot is not None:
        from sqlalchemy.orm import selectinload
        stmt_c = (
            select(LousaCell)
            .options(selectinload(LousaCell.snapshot))
            .where(LousaCell.snapshot_id == snapshot.id)
        )
        for c in (await db.execute(stmt_c)).scalars().all():
            tpa_nome = None
            tpa_matricula = None
            if c.tpa_id is not None:
                tpa = (await db.execute(
                    select(Tpa).where(Tpa.id == c.tpa_id)
                )).scalar_one_or_none()
                if tpa is not None:
                    tpa_nome = tpa.nome_completo
                    tpa_matricula = tpa.matricula_ogmo
            cells.append({
                "id": str(c.id),
                "faina_id": str(c.faina_id),
                "funcao_id": str(c.funcao_id),
                "cais": c.cais,
                "tpa_id": str(c.tpa_id) if c.tpa_id else None,
                "tpa_nome": tpa_nome,
                "tpa_matricula": tpa_matricula,
                "status": c.status_celula.value,
                "data_referencia": c.data_referencia.isoformat(),
            })
        total_tpas = sum(1 for c in cells if c["tpa_id"])

    return {
        "porto": {"id": str(porto_obj.id), "codigo": porto_obj.codigo, "nome": porto_obj.nome_completo},
        "turno": {"id": str(turno_obj.id), "codigo": turno_obj.codigo, "nome": turno_obj.nome_exibicao},
        "snapshot": {
            "id": str(snapshot.id) if snapshot else None,
            "scraped_at": snapshot.scraped_at.isoformat() if snapshot else None,
            "status": snapshot.status.value if snapshot else None,
            "total_celulas": snapshot.total_celulas if snapshot else 0,
            "total_tpas_escalados": snapshot.total_tpas_escalados if snapshot else 0,
        },
        "fainas": [
            {"id": str(f.id), "codigo": f.codigo, "nome": f.nome_exibicao,
             "cor_hex": f.cor_hex, "ordem": f.ordem_lousa}
            for f in fainas
        ],
        "funcoes": [
            {"id": str(f.id), "codigo": f.codigo, "nome": f.nome_exibicao,
             "categoria": f.categoria, "ordem": f.ordem_lousa}
            for f in funcoes
        ],
        "cells": cells,
        "stats": {
            "total_cells": len(cells),
            "total_tpas_escalados": total_tpas,
            "total_fainas": len(fainas),
            "total_funcoes": len(funcoes),
        },
    }


@router.get("/health", summary="Liveness simples (Sprint 0)")
async def health_public() -> dict:
    return {"status": "ok", "scope": "public", "warning": "remover em produção"}


@router.get("/tpa/{matricula}/escala", summary="Escala do TPA (Sprint 0)")
async def tpa_escala(
    matricula: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retorna a escala do TPA: célula de hoje + próximos 7 dias (mock se vazio).

    Sprint 0: usado pelo PWA do TPA. Em Sprint 1 vira autenticado
    com CPF + matrícula OGMO + OTP WhatsApp.
    """
    # 1) TPA
    stmt_t = select(Tpa).where(Tpa.matricula_ogmo == matricula)
    tpa = (await db.execute(stmt_t)).scalar_one_or_none()
    if tpa is None:
        raise HTTPException(404, f"TPA com matrícula {matricula} não encontrado.")

    # 2) Célula de hoje (snapshot mais recente)
    today = date.today()
    cell_hoje: dict | None = None
    stmt_s = (
        select(LousaSnapshot)
        .order_by(LousaSnapshot.scraped_at.desc())
        .limit(1)
    )
    snap = (await db.execute(stmt_s)).scalar_one_or_none()
    if snap is not None:
        stmt_c = (
            select(LousaCell)
            .where(LousaCell.snapshot_id == snap.id, LousaCell.tpa_id == tpa.id)
            .limit(1)
        )
        c = (await db.execute(stmt_c)).scalar_one_or_none()
        if c is not None:
            faina = (await db.execute(select(Faina).where(Faina.id == c.faina_id))).scalar_one_or_none()
            funcao = (await db.execute(select(Funcao).where(Funcao.id == c.funcao_id))).scalar_one_or_none()
            cell_hoje = {
                "faina": faina.nome_exibicao if faina else None,
                "funcao": funcao.nome_exibicao if funcao else None,
                "cais": c.cais,
                "status": c.status_celula.value,
                "data_referencia": c.data_referencia.isoformat(),
            }

    # 3) Próximos 7 dias (mock: gera grade plausível com base em turno + função base)
    proximos_dias: list[dict] = []
    funcao_base = (await db.execute(
        select(Funcao).where(Funcao.id == tpa.funcao_base_id)
    )).scalar_one_or_none()

    for i in range(1, 8):
        d = today + timedelta(days=i)
        # Mock: 70% escalado, 30% folga; sempre turno DIURNO
        escalado = (i % 3) != 0
        proximos_dias.append({
            "data": d.isoformat(),
            "dia_semana": d.strftime("%a"),
            "turno": "DIURNO 08-16" if escalado else None,
            "funcao": funcao_base.nome_exibicao if (escalado and funcao_base) else None,
            "cais": "CAIS 2" if escalado else None,
            "escalado": escalado,
        })

    return {
        "tpa": {
            "id": str(tpa.id),
            "matricula": tpa.matricula_ogmo,
            "nome": tpa.nome_completo,
            "categoria": tpa.categoria,
            "funcao_base": funcao_base.nome_exibicao if funcao_base else None,
        },
        "hoje": {
            "data": today.isoformat(),
            "dia_semana": today.strftime("%a"),
            "turno": "DIURNO 08-16" if cell_hoje else None,
            "celula": cell_hoje,
            "escalado": cell_hoje is not None,
        },
        "proximos_7_dias": proximos_dias,
        "stats_7d": {
            "engajamentos": 5,
            "faltas": 1,
            "recebimentos_brl": 2847.30,
            "posicao_rodizio": 14,
        },
        "links": {
            "fiscal_whatsapp": "https://wa.me/5581999990000?text=Ol%C3%A1%20Fiscal%2C%20preciso%20de%20ajuda",
            "cct_pdf": "/docs/cct-2024-2026.pdf",
        },
    }
