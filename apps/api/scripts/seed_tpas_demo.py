"""SINDESTIVA-PE · Seed rápido de TPAs para teste end-to-end.

Cria 2 TPAs (um out, um in) vinculados a users novos (com role=TPA,
password_hash=NULL — TPA usa só OTP no MVP, D1 do DD v1).
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import session_scope  # noqa: E402
from app.models import Tpa, User  # noqa: E402
from app.models.enums import RoleEnum, TpaStatusEnum, UserStatusEnum  # noqa: E402


TPAS_DEMO = [
    {
        "email": "joao.tpa@example.com",
        "telefone": "+5581988880001",
        "nome_completo": "João Silva",
        "cpf": "11122233396",
        "matricula_ogmo": "TPA-001",
        "funcao_codigo": "TECNICA_01",
        "categoria": "TECNICA",  # era FuncaoCategoriaEnum.TECNICA (removido)
    },
    {
        "email": "maria.tpa@example.com",
        "telefone": "+5581988880002",
        "nome_completo": "Maria Santos",
        "cpf": "22233344485",
        "matricula_ogmo": "TPA-002",
        "funcao_codigo": "MANDO_01",
        "categoria": "MANDO",
    },
]


async def seed() -> dict[str, str]:
    contadores: dict[str, str] = {}
    async with session_scope() as db:
        from app.models import Funcao  # noqa: PLC0415
        for data in TPAS_DEMO:
            # User com role=TPA, password_hash=NULL
            stmt = select(User).where(User.email == data["email"])
            user = (await db.execute(stmt)).scalar_one_or_none()
            if user is None:
                user = User(
                    email=data["email"],
                    telefone=data["telefone"],
                    password_hash=None,  # TPA usa só OTP (D1)
                    role=RoleEnum.TPA,
                    status=UserStatusEnum.ATIVO,
                )
                db.add(user)
                await db.flush()
            else:
                user.role = RoleEnum.TPA
                user.password_hash = None
                user.telefone = data["telefone"]

            # Tpa vinculado
            stmt_t = select(Tpa).where(Tpa.user_id == user.id)
            tpa = (await db.execute(stmt_t)).scalar_one_or_none()
            funcao = (await db.execute(
                select(Funcao).where(Funcao.codigo == data["funcao_codigo"])
            )).scalar_one()
            if tpa is None:
                tpa = Tpa(
                    user_id=user.id,
                    cpf=data["cpf"],
                    nome_completo=data["nome_completo"],
                    matricula_ogmo=data["matricula_ogmo"],
                    telefone=data["telefone"],
                    funcao_base_id=funcao.id,
                    categoria=data["categoria"],
                    status_cadastro=TpaStatusEnum.ATIVO,
                    data_admissao=date.today(),
                    consentimento_at=None,
                    consentimento_versao=None,
                )
                db.add(tpa)
            else:
                tpa.nome_completo = data["nome_completo"]
                tpa.telefone = data["telefone"]
                tpa.funcao_base_id = funcao.id
                tpa.categoria = data["categoria"]
            contadores[data["email"]] = str(user.id)
    return contadores


if __name__ == "__main__":
    import asyncio
    result = asyncio.run(seed())
    print("✅ TPAs demo criados:")
    for email, id_ in result.items():
        print(f"  {email:30} user_id={id_}")
