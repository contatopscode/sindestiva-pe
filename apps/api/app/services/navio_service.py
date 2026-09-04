"""SINDESTIVA-PE · Serviço de catálogo de navios.

Regra central do fix da issue #15: `IntegrityError` do índice único
`uq_navios_imo` NUNCA pode subir cru até o handler default do FastAPI
(que devolve 500 + stacktrace no log e mensagem inútil na UI). Aqui
vira `NavioError` 409 com `code` estável que o front mapeia.

Mesma forma de `RemanejamentoError` (`app.services.remanejamento_service`)
pra manter o contrato de erro `{code, message}` uniforme na API.
"""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Navio

log = get_logger(__name__)


class NavioError(Exception):
    """Erro de negócio do catálogo de navios (vira HTTPException no router)."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


async def criar(
    db: AsyncSession,
    *,
    nome: str,
    imo: str | None = None,
    bandeira: str | None = None,
    tipo_operacao: str | None = None,
) -> Navio:
    """Insere um navio no catálogo.

    Raises:
        NavioError: 409 se o IMO já existe (ou outra constraint estourar).
    """
    navio = Navio(nome=nome, imo=imo, bandeira=bandeira, tipo_operacao=tipo_operacao)
    db.add(navio)
    try:
        await db.flush()
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        detalhe = str(getattr(exc, "orig", exc))
        if "uq_navios_imo" in detalhe or "navios_imo" in detalhe:
            log.warning("navio.criar.imo_duplicado", imo=imo)
            msg = f"Já existe um navio cadastrado com o IMO {imo}."
            raise NavioError(409, "NAVIO_IMO_DUPLICADO", msg) from exc
        log.warning("navio.criar.conflito", nome=nome, detalhe=detalhe)
        msg = "Não foi possível salvar o navio: conflito com um registro existente."
        raise NavioError(409, "NAVIO_CONFLITO", msg) from exc
    except Exception:
        # Qualquer outra falha precisa deixar a sessão limpa — senão o
        # próximo statement morre com "current transaction is aborted".
        await db.rollback()
        log.exception("navio.criar.erro_inesperado", nome=nome)
        raise

    await db.refresh(navio)
    log.info("navio.criado", navio_id=str(navio.id), nome=navio.nome, imo=navio.imo)
    return navio


async def listar(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    q: str | None = None,
) -> tuple[list[Navio], int]:
    """Lista navios (mais recentes primeiro), com busca opcional por
    nome ou IMO."""
    filtros = []
    if q:
        termo = f"%{q.strip()}%"
        filtros.append(or_(Navio.nome.ilike(termo), Navio.imo.ilike(termo)))

    stmt = select(Navio)
    count_stmt = select(func.count()).select_from(Navio)
    for f in filtros:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = (await db.execute(count_stmt)).scalar_one()
    result = await db.execute(stmt.order_by(Navio.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total
