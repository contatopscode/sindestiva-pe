"""SINDESTIVA-PE · Testes de cadastro de navios (issue #15).

Regressão do bug "erro ao salvar no formulário de cadastro de navios".

São testes de UNIDADE puros — não tocam Postgres nem a API live (ao
contrário de `test_lgpd.py`/`test_auth_router.py`, que dependem da API
em :8765). Isso mantém a suíte rodável em CI sem infra:

  - `NavioCreate` (Pydantic v2): normalização e rejeição de payloads
    inválidos ANTES de chegar no banco.
  - `navio_service.criar`: `IntegrityError` (índice único `uq_navios_imo`)
    vira `NavioError` 409 com código estável, e NÃO vaza stacktrace.
"""
from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.schemas.navio import NavioCreate
from app.services.navio_service import NavioError, criar

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fake session (sem DB)
# ---------------------------------------------------------------------------

class FakeSession:
    """AsyncSession mínima: `add`/`flush`/`commit`/`rollback`/`refresh`.

    `flush_exc` permite simular a violação do índice único de IMO.
    """

    def __init__(self, *, flush_exc: Exception | None = None) -> None:
        self.flush_exc = flush_exc
        self.added: list[Any] = []
        self.committed = False
        self.rolled_back = False

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        if self.flush_exc is not None:
            raise self.flush_exc

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True

    async def refresh(self, obj: Any) -> None:
        return None


def _integrity_error(constraint: str = "uq_navios_imo") -> IntegrityError:
    """IntegrityError com a cara do que o asyncpg devolve."""
    return IntegrityError(
        statement="INSERT INTO lousa_main.navios ...",
        params=None,
        orig=Exception(
            f'duplicate key value violates unique constraint "{constraint}"'
        ),
    )


# ---------------------------------------------------------------------------
# NavioCreate — payloads válidos
# ---------------------------------------------------------------------------

def test_navio_create_minimo_so_nome() -> None:
    """Só `nome` é obrigatório — o resto do cadastro é opcional."""
    navio = NavioCreate(nome="MSC Ilona")
    assert navio.nome == "MSC Ilona"
    assert navio.imo is None
    assert navio.bandeira is None
    assert navio.tipo_operacao is None


def test_navio_create_normaliza_nome_com_espacos() -> None:
    """Espaços nas pontas não podem virar nome diferente no banco."""
    assert NavioCreate(nome="  MSC Ilona  ").nome == "MSC Ilona"


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("IMO9319466", "IMO9319466"),
        ("imo9319466", "IMO9319466"),
        ("IMO 9319466", "IMO9319466"),
        ("9319466", "IMO9319466"),
        ("  9319466  ", "IMO9319466"),
    ],
)
def test_navio_create_normaliza_imo(entrada: str, esperado: str) -> None:
    """IMO é normalizado pra `IMO#######` — senão o índice único não
    pega duplicata escrita em formato diferente."""
    assert NavioCreate(nome="Navio X", imo=entrada).imo == esperado


@pytest.mark.parametrize("vazio", ["", "   "])
def test_navio_create_imo_vazio_vira_none(vazio: str) -> None:
    """String vazia vinda do form NÃO pode virar `imo=''` — o índice
    único trataria '' como valor real e o 2º navio sem IMO daria 409."""
    assert NavioCreate(nome="Navio X", imo=vazio).imo is None


@pytest.mark.parametrize("vazio", ["", "   "])
def test_navio_create_bandeira_vazia_vira_none(vazio: str) -> None:
    assert NavioCreate(nome="Navio X", bandeira=vazio).bandeira is None


def test_navio_create_tipo_operacao_uppercase() -> None:
    assert NavioCreate(nome="Navio X", tipo_operacao="container").tipo_operacao == "CONTAINER"


def test_navio_create_ignora_campos_extras() -> None:
    """Payload com campo desconhecido (ex.: front antigo) não deve 422."""
    navio = NavioCreate(nome="Navio X", campo_que_nao_existe="foo")  # type: ignore[call-arg]
    assert navio.nome == "Navio X"


# ---------------------------------------------------------------------------
# NavioCreate — payloads inválidos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nome", ["", "   ", None])
def test_navio_create_nome_obrigatorio(nome: Any) -> None:
    with pytest.raises(ValidationError):
        NavioCreate(nome=nome)


def test_navio_create_nome_muito_longo() -> None:
    with pytest.raises(ValidationError):
        NavioCreate(nome="N" * 201)


@pytest.mark.parametrize(
    "imo",
    [
        "IMO12345",       # 5 dígitos
        "IMO123456789",   # 9 dígitos
        "IMOABCDEFG",     # não numérico
        "93194AB",        # misto
        "IMO-9319466",    # separador inválido
    ],
)
def test_navio_create_imo_invalido(imo: str) -> None:
    with pytest.raises(ValidationError) as exc:
        NavioCreate(nome="Navio X", imo=imo)
    assert "IMO" in str(exc.value)


def test_navio_create_tipo_operacao_invalido() -> None:
    with pytest.raises(ValidationError):
        NavioCreate(nome="Navio X", tipo_operacao="SUBMARINO")


# ---------------------------------------------------------------------------
# navio_service.criar
# ---------------------------------------------------------------------------

async def test_criar_navio_sucesso() -> None:
    session = FakeSession()
    navio = await criar(session, nome="MSC Ilona", imo="IMO9319466")  # type: ignore[arg-type]

    assert navio.nome == "MSC Ilona"
    assert navio.imo == "IMO9319466"
    assert session.added == [navio]
    assert session.committed is True
    assert session.rolled_back is False


async def test_criar_navio_imo_duplicado_vira_409() -> None:
    """Bug original: IntegrityError subia cru → 500 + stacktrace na UI."""
    session = FakeSession(flush_exc=_integrity_error())

    with pytest.raises(NavioError) as exc:
        await criar(session, nome="MSC Ilona", imo="IMO9319466")  # type: ignore[arg-type]

    assert exc.value.status == 409
    assert exc.value.code == "NAVIO_IMO_DUPLICADO"
    assert "IMO9319466" in exc.value.message
    assert "Traceback" not in exc.value.message
    assert session.rolled_back is True
    assert session.committed is False


async def test_criar_navio_integrity_error_generico_vira_409_conflito() -> None:
    """Outra constraint violada também é conflito de dados, não 500."""
    session = FakeSession(flush_exc=_integrity_error(constraint="ck_navios_outro"))

    with pytest.raises(NavioError) as exc:
        await criar(session, nome="MSC Ilona")  # type: ignore[arg-type]

    assert exc.value.status == 409
    assert exc.value.code == "NAVIO_CONFLITO"
    assert session.rolled_back is True


async def test_criar_navio_erro_inesperado_faz_rollback() -> None:
    """Qualquer erro deixa a sessão limpa — senão o próximo request
    dessa sessão quebra com 'transaction aborted'."""
    session = FakeSession(flush_exc=RuntimeError("conexão caiu"))

    with pytest.raises(RuntimeError):
        await criar(session, nome="MSC Ilona")  # type: ignore[arg-type]

    assert session.rolled_back is True
