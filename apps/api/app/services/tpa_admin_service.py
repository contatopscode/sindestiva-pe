"""SINDESTIVA-PE · Gestão admin de TPAs (User + perfil Tpa 1:1)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Funcao, Tpa, User
from app.models.enums import RoleEnum, TpaStatusEnum, UserStatusEnum
from app.schemas.tpa_admin import (
    TpaAdminCreate,
    TpaAdminRead,
    TpaAdminUpdate,
    TpaFuncaoMeta,
)

log = get_logger(__name__)


class TpaAdminError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def _user_status_for_tpa(status: TpaStatusEnum) -> UserStatusEnum:
    if status in (TpaStatusEnum.ATIVO, TpaStatusEnum.AFASTADO):
        return UserStatusEnum.ATIVO
    return UserStatusEnum.INATIVO


def _default_email(cpf: str) -> str:
    return f"tpa+{cpf}@sindestiva.local"


def _serialize_tpa(tpa: Tpa, *, funcao: Funcao) -> TpaAdminRead:
    user = tpa.user
    return TpaAdminRead(
        id=tpa.id,
        user_id=tpa.user_id,
        email=user.email,
        telefone=tpa.telefone,
        user_status=user.status,
        cpf=str(tpa.cpf),
        nome_completo=tpa.nome_completo,
        matricula_ogmo=tpa.matricula_ogmo,
        funcao_base_id=tpa.funcao_base_id,
        funcao_codigo=funcao.codigo,
        funcao_nome=funcao.nome_exibicao,
        categoria=tpa.categoria,
        status_cadastro=tpa.status_cadastro,
        data_nascimento=tpa.data_nascimento,
        data_admissao=tpa.data_admissao,
        data_desligamento=tpa.data_desligamento,
        created_at=tpa.created_at,
        updated_at=tpa.updated_at,
    )


def _map_integrity(exc: IntegrityError) -> TpaAdminError:
    msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
    if "email" in msg or "uq_users_email" in msg:
        return TpaAdminError(409, "EMAIL_DUPLICATE", "E-mail já cadastrado.")
    if "cpf" in msg:
        return TpaAdminError(409, "CPF_DUPLICATE", "CPF já cadastrado.")
    if "matricula_ogmo" in msg or "matricula" in msg:
        return TpaAdminError(
            409, "MATRICULA_DUPLICATE", "Matrícula OGMO já cadastrada."
        )
    return TpaAdminError(409, "CONFLICT", "Conflito de unicidade no cadastro.")


async def _load_funcao(db: AsyncSession, funcao_base_id: UUID) -> Funcao:
    funcao = (
        await db.execute(select(Funcao).where(Funcao.id == funcao_base_id))
    ).scalar_one_or_none()
    if funcao is None or not funcao.is_active:
        raise TpaAdminError(
            422,
            "FUNCAO_INVALIDA",
            "Função base não encontrada ou inativa.",
        )
    return funcao


async def _load_tpa(db: AsyncSession, tpa_id: UUID) -> Tpa | None:
    stmt = (
        select(Tpa)
        .where(Tpa.id == tpa_id, Tpa.deleted_at.is_(None))
        .options(selectinload(Tpa.user))
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_tpa_funcoes(db: AsyncSession) -> list[TpaFuncaoMeta]:
    stmt = select(Funcao).where(Funcao.is_active.is_(True)).order_by(Funcao.ordem_lousa)
    rows = list((await db.execute(stmt)).scalars().all())
    return [TpaFuncaoMeta.model_validate(r) for r in rows]


async def list_admin_tpas(
    db: AsyncSession,
    *,
    q: str | None = None,
    status_cadastro: TpaStatusEnum | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[TpaAdminRead], int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    filters = [
        Tpa.deleted_at.is_(None),
        User.deleted_at.is_(None),
        User.role == RoleEnum.TPA,
    ]
    if status_cadastro is not None:
        filters.append(Tpa.status_cadastro == status_cadastro)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                Tpa.nome_completo.ilike(pattern),
                Tpa.cpf.ilike(pattern),
                Tpa.matricula_ogmo.ilike(pattern),
                User.email.ilike(pattern),
            )
        )

    count_stmt = (
        select(func.count())
        .select_from(Tpa)
        .join(User, Tpa.user_id == User.id)
        .where(*filters)
    )
    total = int((await db.execute(count_stmt)).scalar_one())

    stmt = (
        select(Tpa, Funcao)
        .join(User, Tpa.user_id == User.id)
        .join(Funcao, Tpa.funcao_base_id == Funcao.id)
        .where(*filters)
        .order_by(Tpa.nome_completo)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list((await db.execute(stmt)).all())
    items = [_serialize_tpa(tpa, funcao=funcao) for tpa, funcao in rows]
    return items, total


async def get_admin_tpa(db: AsyncSession, tpa_id: UUID) -> TpaAdminRead:
    stmt = (
        select(Tpa, Funcao)
        .join(User, Tpa.user_id == User.id)
        .join(Funcao, Tpa.funcao_base_id == Funcao.id)
        .where(
            Tpa.id == tpa_id,
            Tpa.deleted_at.is_(None),
            User.deleted_at.is_(None),
            User.role == RoleEnum.TPA,
        )
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        raise TpaAdminError(404, "NOT_FOUND", "TPA não encontrado.")
    tpa, funcao = row
    return _serialize_tpa(tpa, funcao=funcao)


async def create_admin_tpa(db: AsyncSession, data: TpaAdminCreate) -> TpaAdminRead:
    funcao = await _load_funcao(db, data.funcao_base_id)

    cpf_taken = (
        await db.execute(
            select(Tpa.id).where(Tpa.cpf == data.cpf, Tpa.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if cpf_taken is not None:
        raise TpaAdminError(409, "CPF_DUPLICATE", "CPF já cadastrado.")

    mat_taken = (
        await db.execute(
            select(Tpa.id).where(
                Tpa.matricula_ogmo == data.matricula_ogmo,
                Tpa.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if mat_taken is not None:
        raise TpaAdminError(409, "MATRICULA_DUPLICATE", "Matrícula OGMO já cadastrada.")

    email = str(data.email).lower() if data.email else _default_email(data.cpf)
    user_status = _user_status_for_tpa(data.status_cadastro)

    user = User(
        email=email,
        telefone=data.telefone,
        password_hash=None,
        role=RoleEnum.TPA,
        status=user_status,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise _map_integrity(exc) from exc

    tpa = Tpa(
        user_id=user.id,
        cpf=data.cpf,
        nome_completo=data.nome_completo,
        matricula_ogmo=data.matricula_ogmo,
        telefone=data.telefone,
        funcao_base_id=funcao.id,
        categoria=funcao.categoria,
        status_cadastro=data.status_cadastro,
        data_nascimento=data.data_nascimento,
        data_admissao=data.data_admissao,
    )
    db.add(tpa)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _map_integrity(exc) from exc

    await db.refresh(tpa)
    loaded = await get_admin_tpa(db, tpa.id)
    log.info("tpa_admin.created", tpa_id=str(tpa.id), user_id=str(user.id))
    return loaded


async def update_admin_tpa(
    db: AsyncSession,
    tpa_id: UUID,
    data: TpaAdminUpdate,
) -> TpaAdminRead:
    tpa = await _load_tpa(db, tpa_id)
    if tpa is None or tpa.user.role != RoleEnum.TPA:
        raise TpaAdminError(404, "NOT_FOUND", "TPA não encontrado.")

    user = tpa.user
    funcao: Funcao | None = None

    if data.nome_completo is not None:
        tpa.nome_completo = data.nome_completo
    if data.matricula_ogmo is not None:
        tpa.matricula_ogmo = data.matricula_ogmo
    if data.telefone is not None:
        tpa.telefone = data.telefone
        user.telefone = data.telefone
    if data.email is not None:
        user.email = str(data.email).lower()
    if data.data_nascimento is not None:
        tpa.data_nascimento = data.data_nascimento
    if data.data_admissao is not None:
        tpa.data_admissao = data.data_admissao
    if data.data_desligamento is not None:
        tpa.data_desligamento = data.data_desligamento

    if data.funcao_base_id is not None:
        funcao = await _load_funcao(db, data.funcao_base_id)
        tpa.funcao_base_id = funcao.id
        tpa.categoria = funcao.categoria

    if data.status_cadastro is not None:
        tpa.status_cadastro = data.status_cadastro
        user.status = _user_status_for_tpa(data.status_cadastro)
        if (
            data.status_cadastro == TpaStatusEnum.DESLIGADO
            and tpa.data_desligamento is None
        ):
            tpa.data_desligamento = datetime.now(tz=UTC).date()

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _map_integrity(exc) from exc

    log.info("tpa_admin.updated", tpa_id=str(tpa.id))
    return await get_admin_tpa(db, tpa.id)


__all__ = [
    "TpaAdminError",
    "create_admin_tpa",
    "get_admin_tpa",
    "list_admin_tpas",
    "list_tpa_funcoes",
    "update_admin_tpa",
]
