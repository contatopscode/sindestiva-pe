"""SINDESTIVA-PE · Gestão admin de users FISCAL + DIRIGENTE."""
from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.core.security import hash_password
from app.models import Dirigente, Fiscal, Porto, Turno, User
from app.models.enums import FiscalStatusEnum, RoleEnum, UserStatusEnum
from app.schemas.user_admin import AdminUserCreate, AdminUserRead, AdminUserUpdate

log = get_logger(__name__)


class UserAdminError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def _serialize_user(user: User, *, porto_codigo: str | None = None, turno_codigo: str | None = None) -> AdminUserRead:
    nome: str | None = None
    cpf: str | None = None
    matricula: str | None = None
    cargo: str | None = None
    fiscal_status: str | None = None
    data_inicio: date | None = None
    data_inicio_mandato: date | None = None

    if user.fiscal:
        nome = user.fiscal.nome_completo
        cpf = str(user.fiscal.cpf)
        matricula = user.fiscal.matricula_sindicato
        fiscal_status = user.fiscal.status.value
        data_inicio = user.fiscal.data_inicio
        if porto_codigo is None and user.fiscal.porto_id:
            porto_codigo = getattr(user.fiscal, "_porto_codigo", None)
        if turno_codigo is None and user.fiscal.turno_id:
            turno_codigo = getattr(user.fiscal, "_turno_codigo", None)
    if user.dirigente:
        if nome is None:
            nome = user.dirigente.nome_completo
        if cpf is None:
            cpf = str(user.dirigente.cpf)
        if matricula is None:
            matricula = user.dirigente.matricula_sindicato
        cargo = user.dirigente.cargo
        data_inicio_mandato = user.dirigente.data_inicio_mandato

    return AdminUserRead(
        id=user.id,
        email=user.email,
        telefone=user.telefone,
        role=user.role,
        status=user.status,
        nome_completo=nome,
        cpf=cpf,
        matricula_sindicato=matricula,
        cargo=cargo,
        porto_codigo=porto_codigo,
        turno_codigo=turno_codigo,
        fiscal_status=fiscal_status,
        data_inicio=data_inicio,
        data_inicio_mandato=data_inicio_mandato,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def _load_user(db: AsyncSession, user_id: UUID) -> User | None:
    stmt = (
        select(User)
        .where(User.id == user_id, User.deleted_at.is_(None))
        .options(
            selectinload(User.fiscal),
            selectinload(User.dirigente),
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _resolve_porto_turno(
    db: AsyncSession,
    *,
    porto_codigo: str,
    turno_codigo: str,
) -> tuple[Porto, Turno]:
    porto = (
        await db.execute(select(Porto).where(Porto.codigo == porto_codigo))
    ).scalar_one_or_none()
    if porto is None:
        raise UserAdminError(400, "PORTO_INVALIDO", f"Porto '{porto_codigo}' não encontrado.")
    turno = (
        await db.execute(select(Turno).where(Turno.codigo == turno_codigo))
    ).scalar_one_or_none()
    if turno is None:
        raise UserAdminError(400, "TURNO_INVALIDO", f"Turno '{turno_codigo}' não encontrado.")
    return porto, turno


async def _count_active_dirigentes(db: AsyncSession) -> int:
    stmt = select(func.count()).select_from(User).where(
        User.role == RoleEnum.DIRIGENTE,
        User.status == UserStatusEnum.ATIVO,
        User.deleted_at.is_(None),
    )
    return int((await db.execute(stmt)).scalar_one())


async def _guard_last_active_dirigente(
    db: AsyncSession,
    user: User,
    *,
    new_role: RoleEnum | None = None,
    new_status: UserStatusEnum | None = None,
) -> None:
    if user.role != RoleEnum.DIRIGENTE or user.status != UserStatusEnum.ATIVO:
        return
    role_after = new_role or user.role
    status_after = new_status or user.status
    losing_dirigente = (
        role_after != RoleEnum.DIRIGENTE or status_after != UserStatusEnum.ATIVO
    )
    if not losing_dirigente:
        return
    total = await _count_active_dirigentes(db)
    if total <= 1:
        raise UserAdminError(
            409,
            "LAST_ACTIVE_DIRIGENTE",
            "Não é possível desativar ou rebaixar o último DIRIGENTE ativo.",
        )


def _map_integrity(exc: IntegrityError) -> UserAdminError:
    msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
    if "email" in msg or "uq_users_email" in msg:
        return UserAdminError(409, "EMAIL_DUPLICATE", "E-mail já cadastrado.")
    if "cpf" in msg:
        return UserAdminError(409, "CPF_DUPLICATE", "CPF já cadastrado.")
    if "matricula" in msg:
        return UserAdminError(409, "MATRICULA_DUPLICATE", "Matrícula sindicato já cadastrada.")
    return UserAdminError(409, "CONFLICT", "Conflito de unicidade no cadastro.")


async def list_admin_users(db: AsyncSession) -> tuple[list[AdminUserRead], int]:
    stmt = (
        select(User)
        .where(
            User.role.in_([RoleEnum.FISCAL, RoleEnum.DIRIGENTE]),
            User.deleted_at.is_(None),
        )
        .options(selectinload(User.fiscal), selectinload(User.dirigente))
        .order_by(User.role, User.email)
    )
    users = list((await db.execute(stmt)).scalars().all())
    items = [_serialize_user(u) for u in users]
    return items, len(items)


async def get_admin_user(db: AsyncSession, user_id: UUID) -> AdminUserRead:
    user = await _load_user(db, user_id)
    if user is None or user.role not in (RoleEnum.FISCAL, RoleEnum.DIRIGENTE):
        raise UserAdminError(404, "NOT_FOUND", "Usuário não encontrado.")
    return _serialize_user(user)


async def create_admin_user(db: AsyncSession, data: AdminUserCreate) -> AdminUserRead:
    if data.role not in (RoleEnum.FISCAL, RoleEnum.DIRIGENTE):
        raise UserAdminError(400, "INVALID_ROLE", "Somente FISCAL ou DIRIGENTE.")

    today = datetime.now(tz=UTC).date()
    user = User(
        email=str(data.email).lower(),
        telefone=data.telefone,
        password_hash=hash_password(data.password),
        role=data.role,
        status=data.status,
        accepted_terms_at=datetime.now(tz=UTC),
        accepted_terms_version="1.0",
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise _map_integrity(exc) from exc

    try:
        if data.role == RoleEnum.FISCAL:
            porto, turno = await _resolve_porto_turno(
                db, porto_codigo=data.porto_codigo, turno_codigo=data.turno_codigo
            )
            fiscal = Fiscal(
                user_id=user.id,
                cpf=data.cpf,
                nome_completo=data.nome_completo,
                matricula_sindicato=data.matricula_sindicato,
                telefone=data.telefone,
                porto_id=porto.id,
                turno_id=turno.id,
                status=FiscalStatusEnum.ATIVO,
                data_inicio=data.data_inicio or today,
            )
            db.add(fiscal)
        else:
            dirigente = Dirigente(
                user_id=user.id,
                cpf=data.cpf,
                nome_completo=data.nome_completo,
                cargo=data.cargo,
                matricula_sindicato=data.matricula_sindicato,
                data_inicio_mandato=data.data_inicio_mandato or today,
            )
            db.add(dirigente)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _map_integrity(exc) from exc

    await db.refresh(user)
    loaded = await _load_user(db, user.id)
    assert loaded is not None
    log.info("user_admin.created", user_id=str(user.id), role=data.role.value)
    return _serialize_user(loaded)


async def update_admin_user(
    db: AsyncSession,
    user_id: UUID,
    data: AdminUserUpdate,
) -> AdminUserRead:
    user = await _load_user(db, user_id)
    if user is None or user.role not in (RoleEnum.FISCAL, RoleEnum.DIRIGENTE):
        raise UserAdminError(404, "NOT_FOUND", "Usuário não encontrado.")

    new_role = data.role or user.role
    new_status = data.status or user.status
    await _guard_last_active_dirigente(
        db, user, new_role=new_role, new_status=new_status
    )

    if data.email is not None:
        user.email = str(data.email).lower()
    if data.telefone is not None:
        user.telefone = data.telefone
    if data.role is not None:
        user.role = data.role
    if data.status is not None:
        user.status = data.status

    today = datetime.now(tz=UTC).date()
    try:
        if user.role == RoleEnum.FISCAL:
            if user.fiscal is None:
                porto_codigo = data.porto_codigo or "SUAPE"
                turno_codigo = data.turno_codigo or "DIURNO"
                porto, turno = await _resolve_porto_turno(
                    db, porto_codigo=porto_codigo, turno_codigo=turno_codigo
                )
                user.fiscal = Fiscal(
                    user_id=user.id,
                    cpf=data.cpf or "00000000000",
                    nome_completo=data.nome_completo or "Fiscal",
                    matricula_sindicato=data.matricula_sindicato or f"FISCAL-{user.id.hex[:8]}",
                    telefone=data.telefone or user.telefone or "+5500000000000",
                    porto_id=porto.id,
                    turno_id=turno.id,
                    status=FiscalStatusEnum.ATIVO,
                    data_inicio=data.data_inicio or today,
                )
                db.add(user.fiscal)
            else:
                f = user.fiscal
                if data.cpf is not None:
                    f.cpf = data.cpf
                if data.nome_completo is not None:
                    f.nome_completo = data.nome_completo
                if data.matricula_sindicato is not None:
                    f.matricula_sindicato = data.matricula_sindicato
                if data.telefone is not None:
                    f.telefone = data.telefone
                if data.data_inicio is not None:
                    f.data_inicio = data.data_inicio
                if data.porto_codigo or data.turno_codigo:
                    porto, turno = await _resolve_porto_turno(
                        db,
                        porto_codigo=data.porto_codigo or "SUAPE",
                        turno_codigo=data.turno_codigo or "DIURNO",
                    )
                    f.porto_id = porto.id
                    f.turno_id = turno.id
        elif user.role == RoleEnum.DIRIGENTE:
            if user.dirigente is None:
                user.dirigente = Dirigente(
                    user_id=user.id,
                    cpf=data.cpf or "00000000000",
                    nome_completo=data.nome_completo or "Dirigente",
                    cargo=data.cargo or "Dirigente",
                    matricula_sindicato=data.matricula_sindicato or f"DIR-{user.id.hex[:8]}",
                    data_inicio_mandato=data.data_inicio_mandato or today,
                )
                db.add(user.dirigente)
            else:
                d = user.dirigente
                if data.cpf is not None:
                    d.cpf = data.cpf
                if data.nome_completo is not None:
                    d.nome_completo = data.nome_completo
                if data.matricula_sindicato is not None:
                    d.matricula_sindicato = data.matricula_sindicato
                if data.cargo is not None:
                    d.cargo = data.cargo
                if data.data_inicio_mandato is not None:
                    d.data_inicio_mandato = data.data_inicio_mandato

        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _map_integrity(exc) from exc

    loaded = await _load_user(db, user.id)
    assert loaded is not None
    log.info("user_admin.updated", user_id=str(user.id))
    return _serialize_user(loaded)


__all__ = [
    "UserAdminError",
    "create_admin_user",
    "get_admin_user",
    "list_admin_users",
    "update_admin_user",
]
