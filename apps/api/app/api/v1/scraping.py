"""SINDESTIVA-PE · /scraping (disparo manual + status)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.models import LousaEscalaOrigem
from app.models.enums import StatusScrapingEnum
from app.schemas.scraping import (
    ScrapingDispararRequest,
    ScrapingDispararResponse,
    ScrapingStatusItem,
    ScrapingStatusResponse,
)
from app.services.scraping_service import executar_scraping

router = APIRouter(prefix="/scraping", tags=["scraping"])
log = get_logger(__name__)


@router.post(
    "/disparar",
    response_model=ScrapingDispararResponse,
    summary="Dispara scraping manual (Sprint 2 T2-06)",
)
async def disparar(
    payload: ScrapingDispararRequest,
    db: AsyncSession = Depends(get_db),
) -> ScrapingDispararResponse:
    """Dispara 1 ciclo de scraping (1 fonte × 1 porto × 1 turno × 1 data).

    Sprint 2: sem auth (projeto em fase de aprovação — Paulo ativa
    `require_admin` no Sprint 7 quando subir pra staging).
    """
    resultado = await executar_scraping(
        db,
        fonte=payload.fonte,
        porto_slug=payload.porto,
        turno_codigo=payload.turno,
        data=payload.data,
    )
    return ScrapingDispararResponse(
        sucesso=resultado.sucesso,
        escala_origem_id=resultado.escala_origem_id,
        fonte=resultado.fonte,
        porto=resultado.porto_slug,
        turno=resultado.turno_codigo,
        data=resultado.data,
        status=resultado.status,
        total_celulas=resultado.total_celulas,
        duracao_ms=resultado.duracao_ms,
        layout_mudou=resultado.layout_mudou,
        erro_detalhes=resultado.erro_detalhes,
    )


@router.get(
    "/status",
    response_model=ScrapingStatusResponse,
    summary="Status dos últimos scrapes (Sprint 2 T2-07)",
)
async def status(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> ScrapingStatusResponse:
    """Lista os últimos N scrapes (`lousa_escala_origem`) com contagens.

    `limit` default = 20; máximo recomendado = 200.
    """
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=422,
            detail="`limit` deve estar entre 1 e 200.",
        )

    stmt = (
        select(LousaEscalaOrigem)
        .order_by(LousaEscalaOrigem.scraped_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    origens = list(result.scalars().all())

    # Calcula total de alocações por origem (1 round-trip SQL).
    total_celulas_por_origem: dict = {}
    if origens:
        from sqlalchemy import func as sql_func

        from app.models import LousaAlocacao

        count_stmt = (
            select(
                LousaAlocacao.escala_origem_id,
                sql_func.count(LousaAlocacao.id).label("total"),
            )
            .where(LousaAlocacao.escala_origem_id.in_(o.id for o in origens))
            .group_by(LousaAlocacao.escala_origem_id)
        )
        count_result = await db.execute(count_stmt)
        total_celulas_por_origem = {
            row.escala_origem_id: row.total for row in count_result.all()
        }

    itens = [
        ScrapingStatusItem(
            id=o.id,
            fonte=o.fonte,
            data_referencia=o.data_referencia,
            content_hash=o.content_hash,
            status=o.status,
            total_celulas=total_celulas_por_origem.get(o.id, 0),
            duracao_ms=o.duracao_ms,
            scraped_at=o.scraped_at,
            erro_detalhes=o.erro_detalhes,
        )
        for o in origens
    ]

    return ScrapingStatusResponse(
        total=len(itens),
        sucessos=sum(1 for i in itens if i.status == StatusScrapingEnum.SUCESSO),
        falhas=sum(1 for i in itens if i.status == StatusScrapingEnum.FALHA),
        layout_mudou=sum(1 for i in itens if i.status == StatusScrapingEnum.LAYOUT_MUDOU),
        itens=itens,
    )
