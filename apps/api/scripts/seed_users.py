"""SINDESTIVA-PE · Seed de 3 users iniciais (Sprint 1 T1-08/T1-09).

Paulo Siqueira (DTO + DPO), Manoel Costa (Fiscal-piloto), Josias
Santiago (Dirigente/Presidente). Senhas: hash bcrypt 12 rounds.

Roda com:
    python apps/api/scripts/seed_users.py
    python apps/api/scripts/seed_users.py --dry-run

Idempotente: usa upsert por email (citext unique). Pode rodar quantas
vezes quiser.

PORTA: 5442 (pegadinha Mac Paulo) — se estiver rodando em outro lugar,
ajusta DATABASE_URL_ASYNC no .env.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import session_scope  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import Dirigente, Fiscal, User  # noqa: E402
from app.models.enums import FiscalStatusEnum, RoleEnum, TpaStatusEnum, UserStatusEnum  # noqa: E402


# 3 users seed (dev only — em prod, senha vem do convite)
USERS: list[dict] = [
    {
        "email": "paulo@pscode.ia.br",
        "telefone": "+5581999990001",
        "password": "sindestiva-dev-2026",
        "role": RoleEnum.DIRIGENTE,
        "perfil": "dirigente",
        "nome_completo": "Paulo Siqueira",
        "cpf": "11122233396",
        "cargo": "Diretor de Tecnologia e Operação + DPO",
        "is_dpo": True,
    },
    {
        "email": "manoel@sindestiva-pe.com.br",
        "telefone": "+5581999990002",
        "password": "sindestiva-dev-2026",
        "role": RoleEnum.FISCAL,
        "perfil": "fiscal",
        "nome_completo": "Manoel Costa",
        "cpf": "22233344485",
        "matricula_sindicato": "FISCAL-001",
    },
    {
        "email": "josias@sindestiva-pe.com.br",
        "telefone": "+5581999990003",
        "password": "sindestiva-dev-2026",
        "role": RoleEnum.DIRIGENTE,
        "perfil": "dirigente",
        "nome_completo": "Josias Martins Santiago",
        "cpf": "33344455574",
        "cargo": "Presidente do SINDESTIVA-PE",
        "is_dpo": False,
    },
]


async def seed(dry_run: bool = False) -> dict[str, str]:
    """Roda o seed. Retorna mapa email → role."""
    if dry_run:
        return {u["email"]: u["role"].value for u in USERS}

    contadores: dict[str, str] = {}

    async with session_scope() as db:
        for u in USERS:
            user = await _upsert_user(db, u)
            contadores[u["email"]] = user.role.value
            if u["perfil"] == "fiscal":
                await _ensure_fiscal(db, user, u)
            elif u["perfil"] == "dirigente":
                await _ensure_dirigente(db, user, u)

    return contadores


async def _upsert_user(db: AsyncSession, data: dict) -> User:
    """Cria ou atualiza user por email."""
    stmt = select(User).where(User.email == data["email"])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=data["email"],
            telefone=data["telefone"],
            password_hash=hash_password(data["password"]),
            role=data["role"],
            status=UserStatusEnum.ATIVO,
            accepted_terms_at=None,  # forçado a aceitar via API no 1º login
            accepted_terms_version=None,
        )
        db.add(user)
        await db.flush()  # pra ter ID
    else:
        user.password_hash = hash_password(data["password"])
        user.role = data["role"]
        user.telefone = data["telefone"]
        user.status = UserStatusEnum.ATIVO
        await db.flush()

    return user


async def _ensure_fiscal(db: AsyncSession, user: User, data: dict) -> Fiscal:
    """Vincula perfil Fiscal ao user (1:1). Cria se não existir."""
    stmt = select(Fiscal).where(Fiscal.user_id == user.id)
    result = await db.execute(stmt)
    fiscal = result.scalar_one_or_none()
    if fiscal is None:
        from app.models import Porto, Turno  # noqa: PLC0415

        # Pega porto + turno default (Suape + Diurno)
        porto_stmt = select(Porto).where(Porto.codigo == "SUAPE")
        porto = (await db.execute(porto_stmt)).scalar_one()
        turno_stmt = select(Turno).where(Turno.codigo == "DIURNO")
        turno = (await db.execute(turno_stmt)).scalar_one()

        from datetime import date  # noqa: PLC0415

        fiscal = Fiscal(
            user_id=user.id,
            cpf=data["cpf"],
            nome_completo=data["nome_completo"],
            matricula_sindicato=data["matricula_sindicato"],
            telefone=data["telefone"],
            porto_id=porto.id,
            turno_id=turno.id,
            status=FiscalStatusEnum.ATIVO,
            data_inicio=date.today(),
        )
        db.add(fiscal)
        await db.flush()
    return fiscal


async def _ensure_dirigente(db: AsyncSession, user: User, data: dict) -> Dirigente:
    """Vincula perfil Dirigente ao user (1:1). Cria se não existir."""
    stmt = select(Dirigente).where(Dirigente.user_id == user.id)
    result = await db.execute(stmt)
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        from datetime import date  # noqa: PLC0415

        dirigente = Dirigente(
            user_id=user.id,
            cpf=data["cpf"],
            nome_completo=data["nome_completo"],
            cargo=data["cargo"],
            matricula_sindicato=f"DIR-{data['cpf'][:6]}",
            is_dpo=data.get("is_dpo", False),
            data_inicio_mandato=date.today(),
        )
        db.add(dirigente)
        await db.flush()
    else:
        dirigente.is_dpo = data.get("is_dpo", False) or dirigente.is_dpo
    return dirigente


def main() -> None:
    parser = argparse.ArgumentParser(description="SINDESTIVA-PE · seed 3 users iniciais")
    parser.add_argument("--dry-run", action="store_true", help="Imprime plano sem conectar")
    args = parser.parse_args()

    print(f"🌱 SINDESTIVA-PE · seed users (env={settings.app_env})")
    if args.dry_run:
        print("🔍 DRY-RUN (sem conexão ao DB):")
        for u in USERS:
            print(f"  {u['email']:35} role={u['role'].value:10} perfil={u['perfil']}")
        print("✅ Dry-run OK. Remova --dry-run para aplicar.")
        return

    print("🔌 Conectando ao DB...")
    result = asyncio.run(seed(dry_run=False))
    print("✅ Seed concluído:")
    for email, role in result.items():
        print(f"  {email:35} role={role}")
    print()
    print("🔑 Senha de DEV (todos os 3 users): sindestiva-dev-2026")
    print("   ⚠️  TROCAR em prod (S0 K-3: convite com senha provisória)")


if __name__ == "__main__":
    main()
