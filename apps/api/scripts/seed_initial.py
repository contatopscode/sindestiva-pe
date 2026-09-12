#!/usr/bin/env python3
# =============================================================================
# SINDESTIVA-PE · Seed inicial idempotente (Coolify/prod)
#
# Diferente do `run-seeds.sh` (que roda os 3 seeds em sequência):
# Este script é IDEMPOTENTE — só popula se a tabela estiver vazia.
# Usado pelo entrypoint.sh da API no startup do container.
#
# Idempotência: checa `SELECT COUNT(*) FROM users` antes de inserir.
# Se > 0, pula. Assim, restart do container não duplica dados.
#
# Referência: DIAGNOSTICO-FUNCIONAL-2026-09-07.md §2.3 (seeds nunca rodaram em prod)
# =============================================================================

import asyncio
import os
import sys

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Adiciona /app ao path pra importar app.*
sys.path.insert(0, "/app")

from app.core.config import settings  # noqa: E402
from app.core.autenticacao import gerar_hash_senha  # noqa: E402
from app.db.base import BaseMain  # noqa: E402
import app.db.modelos as m  # noqa: E402


async def tabela_vazia(session: AsyncSession, modelo) -> bool:
    """Retorna True se a tabela do modelo está vazia."""
    result = await session.execute(select(func.count()).select_from(modelo))
    count = result.scalar_one()
    return count == 0


async def seed_se_vazio():
    """Popula dados iniciais APENAS se as tabelas estiverem vazias."""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Users essenciais (Paulo/Manoel/Josias)
        if await tabela_vazia(session, m.Usuario):
            print("    → Inserindo users iniciais (Paulo/Manoel/Josias)...")
            users = [
                m.Usuario(
                    nome="Paulo Siqueira",
                    email="paulo@pscode.ia.br",
                    senha_hash=gerar_hash_senha("sindestiva-dev-2026"),
                    papel="PLATAFORMA",
                    ativo=True,
                ),
                m.Usuario(
                    nome="Manoel Costa",
                    email="manoel@pscode.ia.br",
                    senha_hash=gerar_hash_senha("sindestiva-dev-2026"),
                    papel="FISCAL",
                    ativo=True,
                ),
                m.Usuario(
                    nome="Josias Santiago",
                    email="josias@pscode.ia.br",
                    senha_hash=gerar_hash_senha("sindestiva-dev-2026"),
                    papel="DIRIGENTE",
                    ativo=True,
                ),
            ]
            session.add_all(users)
            await session.commit()
        else:
            print("    → Users já populados (pulando)")

        # 2. TPAs demo
        if await tabela_vazia(session, m.Tpa):
            print("    → Inserindo TPAs demo (TPA-001/TPA-002)...")
            tpas = [
                m.Tpa(matricula="TPA-001", nome="João Silva", categoria="ESTIVADOR", ativo=True),
                m.Tpa(matricula="TPA-002", nome="Maria Santos", categoria="ARRUMADOR", ativo=True),
            ]
            session.add_all(tpas)
            await session.commit()
        else:
            print("    → TPAs já populados (pulando)")

        # 3. Catálogos (portos, turnos, funções, fainas)
        # Estes são populados pelo seed_catalogos.py tradicional — não duplicar aqui.
        # O `run-seeds.sh` (chamado manualmente) cuida disso.

    await engine.dispose()
    print("    ✓ Seed inicial OK")


if __name__ == "__main__":
    try:
        asyncio.run(seed_se_vazio())
    except Exception as e:
        print(f"ERRO: seed_initial falhou: {e}", file=sys.stderr)
        sys.exit(1)
