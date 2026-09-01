"""SINDESTIVA-PE · Seed dos 5 catálogos (Sprint 1 T1-03).

Roda com:
    python apps/api/scripts/seed_catalogos.py
    python apps/api/scripts/seed_catalogos.py --dry-run

Idempotente: usa `INSERT ... ON CONFLICT (coluna_unique) DO NOTHING`
em todas as inserções. Pode rodar quantas vezes quiser.

TODO(D5): 10 fainas e 26 funções ainda em aberto — Manoel Costa
confirma (K-3 do plano). Por ora uso placeholders que mapeiam 1:1 com
o protótipo HTML. Quando Manoel confirmar, ajustar este seed e
rodar `alembic upgrade head` novamente (idempotente — só atualiza o
que mudou).

TODO(D4): turno intermediário? Manoel confirma. Por ora 2 turnos.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, time
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

# Permite rodar tanto como `python scripts/seed_catalogos.py`
# (precisa sys.path) quanto como módulo.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.database import session_scope  # noqa: E402
from app.models import (  # noqa: E402
    Faina,
    FeriadoNacional,
    Funcao,
    Porto,
    Turno,
)

SCHEMA = "lousa_main"


# ---------------------------------------------------------------------------
# Dados dos catálogos
# ---------------------------------------------------------------------------

PORTOS: list[dict[str, Any]] = [
    {
        "codigo": "SUAPE",
        "nome_completo": "Porto de Suape",
        "cnpj_ogmo": "02.324.975/0001-37",  # público, OGMO/PE
        "url_tpa": "http://tpa.ogmosuape.com.br",
        "url_escalanet": None,
        "is_active": True,
    },
    {
        "codigo": "RECIFE",
        "nome_completo": "Porto do Recife",
        "cnpj_ogmo": "02.324.975/0001-37",  # mesmo OGMO
        "url_tpa": None,
        "url_escalanet": "http://escalanet.recife.gov.br",
        "is_active": True,
    },
]

TURNOS: list[dict[str, Any]] = [
    {
        "codigo": "DIURNO",
        "nome_exibicao": "08-16",
        "hora_inicio": time(8, 0),
        "hora_fim": time(16, 0),
        "duracao_horas": Decimal("8.00"),
    },
    {
        "codigo": "NOTURNO",
        "nome_exibicao": "20-04",
        "hora_inicio": time(20, 0),
        "hora_fim": time(4, 0),
        "duracao_horas": Decimal("8.00"),
    },
    # TODO(D4): turno intermediário (16-20 ou 04-08)?
]


def _funcoes_seed() -> list[dict[str, Any]]:
    """26 funções (D5 em aberto; placeholders alinhados com protótipo).

    Mando 6 + Terno 6 + Técnica 12 + Vigia 2 = 26.
    """
    base: list[tuple[str, str, str, int]] = [
        # Mando (6)
        ("MANDO_01", "C/M Geral", "MANDO", 1),
        ("MANDO_02", "C/M Porão", "MANDO", 2),
        ("MANDO_03", "C/M Bloco", "MANDO", 3),
        ("MANDO_04", "C/M Rechego", "MANDO", 4),
        ("MANDO_05", "C/M Cons.", "MANDO", 5),
        ("MANDO_06", "Supervisor", "MANDO", 6),
        # Terno (6)
        ("TERNO_01", "Porão", "TERNO", 7),
        ("TERNO_02", "Bloco MAX", "TERNO", 8),
        ("TERNO_03", "Bloco", "TERNO", 9),
        ("TERNO_04", "Rechego", "TERNO", 10),
        ("TERNO_05", "Cons.", "TERNO", 11),
        ("TERNO_06", "Ship Loader", "TERNO", 12),
        # Técnica (12)
        ("TECNICA_01", "Sinaleiro", "TECNICA", 13),
        ("TECNICA_02", "Guincho A", "TECNICA", 14),
        ("TECNICA_03", "Guincho B", "TECNICA", 15),
        ("TECNICA_04", "Emp. GP", "TECNICA", 16),
        ("TECNICA_05", "Emp. PP", "TECNICA", 17),
        ("TECNICA_06", "V. Pesado", "TECNICA", 18),
        ("TECNICA_07", "V. Leve", "TECNICA", 19),
        ("TECNICA_08", "Manobrista", "TECNICA", 20),
        ("TECNICA_09", "Transp.", "TECNICA", 21),
        ("TECNICA_10", "Pá Mec.", "TECNICA", 22),
        # 2 a definir com Manoel (D5)
        ("TECNICA_11", "Técnica 11 (a definir c/ Manoel)", "TECNICA", 23),
        ("TECNICA_12", "Técnica 12 (a definir c/ Manoel)", "TECNICA", 24),
        # Vigia (2)
        ("VIGIA_01", "Vigia Porto", "VIGIA", 25),
        ("VIGIA_02", "Vigia Cais", "VIGIA", 26),
    ]
    return [
        {
            "codigo": codigo,
            "nome_exibicao": nome,
            "categoria": cat,
            "ordem_lousa": ordem,
            "is_active": True,
        }
        for codigo, nome, cat, ordem in base
    ]


def _fainas_seed() -> list[dict[str, Any]]:
    """10 fainas (D5 — protótipo lista 8 por nome, 2 placeholders)."""
    base: list[tuple[str, str, str | None, int]] = [
        ("PRODUCAO", "Produção", "#2563eb", 1),
        ("SALARIO", "Salário", "#16a34a", 2),
        ("SACARIA", "Sacaria", "#ca8a04", 3),
        ("VEICULO", "Veículo", "#9333ea", 4),
        ("DIVERSOS", "Diversos", "#64748b", 5),
        ("CADASTRO", "Cadastro", "#0891b2", 6),
        ("SUPLEMENTAR", "Suplementar", "#db2777", 7),
        ("ALTURA", "Altura", "#ea580c", 8),
        # 2 a confirmar com Manoel
        ("FAINA_09", "Faina 9 (a definir c/ Manoel)", None, 9),
        ("FAINA_10", "Faina 10 (a definir c/ Manoel)", None, 10),
    ]
    return [
        {
            "codigo": codigo,
            "nome_exibicao": nome,
            "cor_hex": cor,
            "ordem_lousa": ordem,
            "is_active": True,
        }
        for codigo, nome, cor, ordem in base
    ]


# Feriados nacionais 2026-2027 (hard-coded; se crescer, mover pra DB +
# job anual). Tipos: NACIONAL / ESTADUAL_PE / MUNICIPAL_SUAPE / MUNICIPAL_RECIFE.
FERIADOS: list[dict[str, Any]] = [
    {"data": date(2026, 1, 1), "nome": "Confraternização Universal", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2026, 4, 21), "nome": "Tiradentes", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2026, 5, 1), "nome": "Dia do Trabalho", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2026, 9, 7), "nome": "Independência do Brasil", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2026, 10, 12), "nome": "N. Sra. Aparecida", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2026, 11, 2), "nome": "Finados", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2026, 11, 15), "nome": "Proclamação da República", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2026, 12, 25), "nome": "Natal", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2027, 1, 1), "nome": "Confraternização Universal", "tipo": "NACIONAL", "is_recorrente": True},
    # Pernambuco
    {"data": date(2026, 3, 6), "nome": "Revolução Pernambucana (1824)", "tipo": "ESTADUAL_PE", "is_recorrente": True},
    {"data": date(2026, 6, 24), "nome": "São João (PE)", "tipo": "ESTADUAL_PE", "is_recorrente": True},
    # Recife / Suape (pontuais)
    {"data": date(2026, 3, 8), "nome": "Aniversário do Recife", "tipo": "MUNICIPAL_RECIFE", "is_recorrente": True},
    {"data": date(2026, 7, 16), "nome": "Aniversário de Suape", "tipo": "MUNICIPAL_SUAPE", "is_recorrente": True},
    # 2 extras pra completar 15
    {"data": date(2027, 4, 21), "nome": "Tiradentes", "tipo": "NACIONAL", "is_recorrente": True},
    {"data": date(2027, 5, 1), "nome": "Dia do Trabalho", "tipo": "NACIONAL", "is_recorrente": True},
]


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

async def _upsert(db: AsyncSession, model: type, rows: list[dict], conflict: str) -> int:
    """Insere `rows` no model com ON CONFLICT DO NOTHING. Retorna # inseridos.

    Usa o `pg_insert` no `Table` subjacente (não em text()) pra que o
    SQLAlchemy 2 consiga compilar a query com o tipo correto das colunas
    (essencial pra CITEXT, TIMESTAMP WITH TIME ZONE, etc).
    """
    if not rows:
        return 0
    table = model.__table__
    stmt = pg_insert(table).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=[conflict])
    result = await db.execute(stmt)
    # Heurística: pg_insert com asyncpg pode não retornar rowcount preciso.
    return result.rowcount if result.rowcount is not None else len(rows)


async def seed(dry_run: bool = False) -> dict[str, int]:
    """Roda o seed completo. Retorna contadores por tabela."""
    if dry_run:
        return {
            "portos": len(PORTOS),
            "turnos": len(TURNOS),
            "funcoes": len(_funcoes_seed()),
            "fainas": len(_fainas_seed()),
            "feriados_nacionais": len(FERIADOS),
            "dry_run": 1,
        }

    funcoes = _funcoes_seed()
    fainas = _fainas_seed()
    contadores: dict[str, int] = {}

    async with session_scope() as db:
        contadores["portos"] = await _upsert(db, Porto, PORTOS, "codigo")
        contadores["turnos"] = await _upsert(db, Turno, TURNOS, "codigo")
        contadores["funcoes"] = await _upsert(db, Funcao, funcoes, "codigo")
        contadores["fainas"] = await _upsert(db, Faina, fainas, "codigo")
        contadores["feriados_nacionais"] = await _upsert(
            db, FeriadoNacional, FERIADOS, "data"
        )

    return contadores


def main() -> None:
    parser = argparse.ArgumentParser(description="SINDESTIVA-PE · seed catálogos")
    parser.add_argument("--dry-run", action="store_true", help="Imprime plano sem conectar")
    args = parser.parse_args()

    print(f"🌱 SINDESTIVA-PE · seed catálogos (env={settings.app_env}, schema={SCHEMA})")
    if args.dry_run:
        result = asyncio.run(seed(dry_run=True))
        print("🔍 DRY-RUN (sem conexão ao DB):")
        for k, v in result.items():
            print(f"  {k}: {v}")
        print("✅ Dry-run OK. Remova --dry-run para aplicar.")
        return

    print("🔌 Conectando ao DB...")
    result = asyncio.run(seed(dry_run=False))
    print("✅ Seed concluído:")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
