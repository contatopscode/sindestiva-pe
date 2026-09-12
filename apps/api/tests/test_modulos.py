"""SINDESTIVA-PE · Testes de Gestão de usuários por módulo (issue #14).

Cobre:
  - Funções puras da policy de permissão (sem DB): hierarquia de papéis,
    bypass de DIRIGENTE, resolução por slug.
  - Cache de permissões (TTL + invalidação).
  - Schemas Pydantic (rejeita payload inválido).
  - Model `UsuarioModulo` (FK + unique constraint) contra `lousa_main`.
  - Endpoints via API live (RBAC 401/403, CRUD, matriz, revogação).

Convenção de naming (mesma de `test_bi.py`):
  `test_modulos_puro_*`  → funções puras
  `test_modulos_io_*`    → I/O em DB
  `test_modulos_api_*`   → integração com API live
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    NIVEL_PAPEL,
    CachePermissoes,
    is_superusuario,
    nivel_papel,
    papel_satisfaz,
    pode_acessar,
)
from app.models import Modulo, RoleEnum, UsuarioModulo, User
from app.models.enums import ModuloPapelEnum
from app.schemas.modulo import (
    AtribuicaoCreate,
    ModuloCreate,
    ModuloUpdate,
)

# ---------------------------------------------------------------------------
# 1. Funções puras — hierarquia de papéis
# ---------------------------------------------------------------------------


def test_modulos_puro_hierarquia_papeis_ordenada() -> None:
    """VISUALIZAR < EDITAR < ADMIN — a ordem é o que a policy usa."""
    assert NIVEL_PAPEL[ModuloPapelEnum.VISUALIZAR] < NIVEL_PAPEL[ModuloPapelEnum.EDITAR]
    assert NIVEL_PAPEL[ModuloPapelEnum.EDITAR] < NIVEL_PAPEL[ModuloPapelEnum.ADMIN]


def test_modulos_puro_nivel_papel_aceita_str_e_enum() -> None:
    """A policy recebe papel vindo do DB (enum) ou do JWT/JSON (str)."""
    assert nivel_papel(ModuloPapelEnum.EDITAR) == nivel_papel("EDITAR")


def test_modulos_puro_nivel_papel_desconhecido_e_zero() -> None:
    """Papel desconhecido nunca satisfaz nada (fail-closed)."""
    assert nivel_papel("SUPER_HACKER") == 0


@pytest.mark.parametrize(
    ("usuario", "minimo", "esperado"),
    [
        (ModuloPapelEnum.ADMIN, ModuloPapelEnum.VISUALIZAR, True),
        (ModuloPapelEnum.ADMIN, ModuloPapelEnum.ADMIN, True),
        (ModuloPapelEnum.EDITAR, ModuloPapelEnum.VISUALIZAR, True),
        (ModuloPapelEnum.EDITAR, ModuloPapelEnum.EDITAR, True),
        (ModuloPapelEnum.EDITAR, ModuloPapelEnum.ADMIN, False),
        (ModuloPapelEnum.VISUALIZAR, ModuloPapelEnum.EDITAR, False),
        (ModuloPapelEnum.VISUALIZAR, ModuloPapelEnum.ADMIN, False),
    ],
)
def test_modulos_puro_papel_satisfaz(
    usuario: ModuloPapelEnum, minimo: ModuloPapelEnum, esperado: bool
) -> None:
    """`papel_satisfaz` é o coração da policy: papel do user >= mínimo exigido."""
    assert papel_satisfaz(usuario, minimo) is esperado


def test_modulos_puro_papel_satisfaz_sem_atribuicao_e_false() -> None:
    """Sem papel (None) = sem acesso. Fail-closed."""
    assert papel_satisfaz(None, ModuloPapelEnum.VISUALIZAR) is False


# ---------------------------------------------------------------------------
# 2. Funções puras — superusuário e `pode_acessar`
# ---------------------------------------------------------------------------


def test_modulos_puro_dirigente_e_superusuario() -> None:
    """DIRIGENTE (Josias/Paulo) é admin da plataforma."""
    assert is_superusuario(RoleEnum.DIRIGENTE) is True
    assert is_superusuario("DIRIGENTE") is True


def test_modulos_puro_fiscal_e_tpa_nao_sao_superusuario() -> None:
    assert is_superusuario(RoleEnum.FISCAL) is False
    assert is_superusuario(RoleEnum.TPA) is False
    assert is_superusuario(None) is False


def test_modulos_puro_dirigente_acessa_qualquer_modulo() -> None:
    """Bypass do superusuário: DIRIGENTE não precisa de atribuição explícita."""
    assert (
        pode_acessar(
            role=RoleEnum.DIRIGENTE,
            atribuicoes={},
            slug="lousa",
            papel_minimo=ModuloPapelEnum.ADMIN,
        )
        is True
    )


def test_modulos_puro_fiscal_com_atribuicao_suficiente_acessa() -> None:
    assert (
        pode_acessar(
            role=RoleEnum.FISCAL,
            atribuicoes={"lousa": ModuloPapelEnum.EDITAR},
            slug="lousa",
            papel_minimo=ModuloPapelEnum.VISUALIZAR,
        )
        is True
    )


def test_modulos_puro_fiscal_com_papel_insuficiente_nao_acessa() -> None:
    """Critério de aceite: papel abaixo do mínimo → bloqueado (vira 403)."""
    assert (
        pode_acessar(
            role=RoleEnum.FISCAL,
            atribuicoes={"remanejamentos": ModuloPapelEnum.VISUALIZAR},
            slug="remanejamentos",
            papel_minimo=ModuloPapelEnum.EDITAR,
        )
        is False
    )


def test_modulos_puro_fiscal_sem_atribuicao_no_modulo_nao_acessa() -> None:
    """Atribuição em OUTRO módulo não dá acesso ao módulo pedido."""
    assert (
        pode_acessar(
            role=RoleEnum.FISCAL,
            atribuicoes={"lousa": ModuloPapelEnum.ADMIN},
            slug="bi",
            papel_minimo=ModuloPapelEnum.VISUALIZAR,
        )
        is False
    )


# ---------------------------------------------------------------------------
# 3. Cache de permissões (risco do plano: "degradar performance sem cache")
# ---------------------------------------------------------------------------


def test_modulos_puro_cache_guarda_e_devolve() -> None:
    cache = CachePermissoes(ttl_segundos=60)
    uid = str(uuid4())
    cache.set(uid, {"lousa": ModuloPapelEnum.EDITAR})
    assert cache.get(uid) == {"lousa": ModuloPapelEnum.EDITAR}


def test_modulos_puro_cache_miss_devolve_none() -> None:
    cache = CachePermissoes(ttl_segundos=60)
    assert cache.get(str(uuid4())) is None


def test_modulos_puro_cache_expira_por_ttl() -> None:
    """TTL zerado = sempre expirado (não deixa permissão velha viva)."""
    cache = CachePermissoes(ttl_segundos=0)
    uid = str(uuid4())
    cache.set(uid, {"lousa": ModuloPapelEnum.ADMIN})
    assert cache.get(uid) is None


def test_modulos_puro_cache_invalidate_remove_usuario() -> None:
    """Critério de aceite: revogar permissão → usuário perde acesso na hora."""
    cache = CachePermissoes(ttl_segundos=600)
    uid_a, uid_b = str(uuid4()), str(uuid4())
    cache.set(uid_a, {"lousa": ModuloPapelEnum.ADMIN})
    cache.set(uid_b, {"bi": ModuloPapelEnum.VISUALIZAR})
    cache.invalidate(uid_a)
    assert cache.get(uid_a) is None
    assert cache.get(uid_b) is not None


def test_modulos_puro_cache_invalidate_all() -> None:
    cache = CachePermissoes(ttl_segundos=600)
    cache.set(str(uuid4()), {"lousa": ModuloPapelEnum.ADMIN})
    cache.invalidate_all()
    assert cache.size() == 0


# ---------------------------------------------------------------------------
# 4. Schemas Pydantic — rejeita payload inválido
# ---------------------------------------------------------------------------


def test_modulos_puro_schema_modulo_create_valido() -> None:
    m = ModuloCreate(slug="financeiro", nome="Financeiro")
    assert m.slug == "financeiro"
    assert m.ativo is True


def test_modulos_puro_schema_modulo_create_normaliza_slug() -> None:
    """Slug é chave funcional na policy — normalizado pra lowercase/trim."""
    m = ModuloCreate(slug="  Financeiro  ", nome="Financeiro")
    assert m.slug == "financeiro"


@pytest.mark.parametrize(
    "slug_invalido",
    ["", "  ", "com espaço", "MAIÚSCULA_ACENTO_ç", "slug/barra", "a" * 65],
)
def test_modulos_puro_schema_modulo_create_rejeita_slug_invalido(slug_invalido: str) -> None:
    """Slug precisa casar `^[a-z0-9][a-z0-9_-]*$` e caber em 64 chars."""
    with pytest.raises(ValidationError):
        ModuloCreate(slug=slug_invalido, nome="X")


def test_modulos_puro_schema_modulo_create_rejeita_nome_vazio() -> None:
    with pytest.raises(ValidationError):
        ModuloCreate(slug="valido", nome="")


def test_modulos_puro_schema_atribuicao_rejeita_papel_invalido() -> None:
    """Papel fora do enum → 422 (não vira INSERT quebrado)."""
    with pytest.raises(ValidationError):
        AtribuicaoCreate(user_id=uuid4(), modulo_id=uuid4(), papel="SUPER_ADMIN")


def test_modulos_puro_schema_atribuicao_rejeita_uuid_invalido() -> None:
    with pytest.raises(ValidationError):
        AtribuicaoCreate(user_id="nao-e-uuid", modulo_id=uuid4(), papel="ADMIN")


def test_modulos_puro_schema_atribuicao_valido() -> None:
    a = AtribuicaoCreate(user_id=uuid4(), modulo_id=uuid4(), papel="EDITAR")
    assert a.papel is ModuloPapelEnum.EDITAR


def test_modulos_puro_schema_update_rejeita_payload_vazio() -> None:
    """PATCH sem nenhum campo é erro de cliente, não no-op silencioso."""
    with pytest.raises(ValidationError):
        ModuloUpdate()


def test_modulos_puro_schema_update_aceita_desativacao() -> None:
    """Critério de aceite: admin desativa módulo (soft, via `ativo=False`)."""
    u = ModuloUpdate(ativo=False)
    assert u.ativo is False


# ---------------------------------------------------------------------------
# 5. Model — FK + unique constraint (I/O em lousa_main)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_modulos_io_unique_user_modulo(
    db_session: AsyncSession, manoel_user: User
) -> None:
    """`uq_usuario_modulos_user_modulo` impede atribuição duplicada."""
    modulo = Modulo(slug=f"teste-uq-{uuid4().hex[:8]}", nome="Teste UQ")
    db_session.add(modulo)
    await db_session.flush()

    db_session.add(
        UsuarioModulo(
            user_id=manoel_user.id,
            modulo_id=modulo.id,
            papel=ModuloPapelEnum.VISUALIZAR,
        )
    )
    await db_session.flush()

    db_session.add(
        UsuarioModulo(
            user_id=manoel_user.id,
            modulo_id=modulo.id,
            papel=ModuloPapelEnum.ADMIN,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_modulos_io_fk_user_inexistente(
    db_session: AsyncSession,
) -> None:
    """FK pra `users.id` — user fantasma não pode receber permissão."""
    modulo = Modulo(slug=f"teste-fk-{uuid4().hex[:8]}", nome="Teste FK")
    db_session.add(modulo)
    await db_session.flush()

    db_session.add(
        UsuarioModulo(
            user_id=uuid4(),  # não existe em lousa_main.users
            modulo_id=modulo.id,
            papel=ModuloPapelEnum.VISUALIZAR,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_modulos_io_slug_unico(db_session: AsyncSession) -> None:
    """Slug é chave funcional da policy — não pode duplicar."""
    slug = f"teste-slug-{uuid4().hex[:8]}"
    db_session.add(Modulo(slug=slug, nome="Primeiro"))
    await db_session.flush()
    db_session.add(Modulo(slug=slug, nome="Segundo"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_modulos_io_seed_da_migration_presente(db_session: AsyncSession) -> None:
    """Migration 0004 semeia os módulos que já existem no sistema."""
    rows = await db_session.execute(
        text("SELECT slug FROM lousa_main.modulos WHERE ativo IS TRUE")
    )
    slugs = {r[0] for r in rows}
    assert {"lousa", "remanejamentos", "ogmo", "auditoria", "bi"} <= slugs


# ---------------------------------------------------------------------------
# 6. API live — RBAC, CRUD, matriz, revogação
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_modulos_api_lista_exige_auth(client: httpx.AsyncClient) -> None:
    """Sem Bearer → 401."""
    resp = await client.get("/api/v1/modulos")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_modulos_api_lista_modulos_do_usuario(
    client: httpx.AsyncClient, api_token_paulo: str
) -> None:
    """Critério de aceite: GET /modulos lista módulos do usuário autenticado."""
    resp = await client.get(
        "/api/v1/modulos",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body
    # Paulo é DIRIGENTE (superusuário) → enxerga todos os módulos ativos.
    slugs = {i["slug"] for i in body["items"]}
    assert "lousa" in slugs
    assert all("papel" in i for i in body["items"])


@pytest.mark.asyncio
async def test_modulos_api_fiscal_nao_cria_modulo(
    client: httpx.AsyncClient, api_token_manoel: str
) -> None:
    """Critério de aceite: rota protegida sem permissão → 403."""
    resp = await client.post(
        "/api/v1/modulos",
        headers={"Authorization": f"Bearer {api_token_manoel}"},
        json={"slug": f"proibido-{uuid4().hex[:6]}", "nome": "Proibido"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_modulos_api_ciclo_completo_admin(
    client: httpx.AsyncClient, api_token_paulo: str, api_token_manoel: str
) -> None:
    """E2E: admin cria módulo → atribui ao Manoel → Manoel acessa → revoga → 403.

    Cobre 3 cenários E2E do plano de testes numa única sessão (o estado
    é sequencial: criar → atribuir → revogar).
    """
    h_admin = {"Authorization": f"Bearer {api_token_paulo}"}
    h_fiscal = {"Authorization": f"Bearer {api_token_manoel}"}
    slug = f"e2e-{uuid4().hex[:8]}"

    # 1) Admin cria o módulo.
    resp = await client.post(
        "/api/v1/modulos", headers=h_admin, json={"slug": slug, "nome": "Módulo E2E"}
    )
    assert resp.status_code == 201, resp.text
    modulo_id = resp.json()["id"]

    # 2) Antes de atribuir, o Fiscal não tem acesso ao módulo.
    resp = await client.get(
        f"/api/v1/modulos/{modulo_id}/acesso", headers=h_fiscal
    )
    assert resp.status_code == 403

    # 3) Descobre o user_id do Manoel pela matriz (admin-only).
    resp = await client.get("/api/v1/modulos/matriz", headers=h_admin)
    assert resp.status_code == 200, resp.text
    matriz = resp.json()
    assert any(m["id"] == modulo_id for m in matriz["modulos"])
    manoel = next(
        u for u in matriz["usuarios"] if u["email"] == "manoel@sindestiva-pe.com.br"
    )

    # 4) Admin atribui o Fiscal ao módulo com papel EDITAR.
    resp = await client.post(
        "/api/v1/modulos/atribuicoes",
        headers=h_admin,
        json={"user_id": manoel["id"], "modulo_id": modulo_id, "papel": "EDITAR"},
    )
    assert resp.status_code == 201, resp.text

    # 5) Agora o Fiscal acessa a rota protegida do módulo.
    resp = await client.get(f"/api/v1/modulos/{modulo_id}/acesso", headers=h_fiscal)
    assert resp.status_code == 200, resp.text
    assert resp.json()["papel"] == "EDITAR"

    # 6) O módulo aparece em GET /modulos do Fiscal.
    resp = await client.get("/api/v1/modulos", headers=h_fiscal)
    assert resp.status_code == 200
    assert slug in {i["slug"] for i in resp.json()["items"]}

    # 7) Admin revoga → acesso cai na hora (cache invalidado).
    resp = await client.delete(
        f"/api/v1/modulos/atribuicoes/{manoel['id']}/{modulo_id}", headers=h_admin
    )
    assert resp.status_code == 204, resp.text

    resp = await client.get(f"/api/v1/modulos/{modulo_id}/acesso", headers=h_fiscal)
    assert resp.status_code == 403

    # 8) Admin desativa o módulo (cleanup + critério de aceite).
    resp = await client.patch(
        f"/api/v1/modulos/{modulo_id}", headers=h_admin, json={"ativo": False}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["ativo"] is False


@pytest.mark.asyncio
async def test_modulos_api_matriz_exige_admin(
    client: httpx.AsyncClient, api_token_manoel: str
) -> None:
    """Matriz expõe todos os users × módulos — só DIRIGENTE."""
    resp = await client.get(
        "/api/v1/modulos/matriz",
        headers={"Authorization": f"Bearer {api_token_manoel}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_modulos_api_slug_duplicado_retorna_409(
    client: httpx.AsyncClient, api_token_paulo: str
) -> None:
    """Slug já existente → 409 (não 500 por IntegrityError vazando)."""
    h = {"Authorization": f"Bearer {api_token_paulo}"}
    resp = await client.post(
        "/api/v1/modulos", headers=h, json={"slug": "lousa", "nome": "Duplicado"}
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_modulos_api_atribuicao_modulo_inexistente_404(
    client: httpx.AsyncClient, api_token_paulo: str, manoel_user: User
) -> None:
    resp = await client.post(
        "/api/v1/modulos/atribuicoes",
        headers={"Authorization": f"Bearer {api_token_paulo}"},
        json={
            "user_id": str(manoel_user.id),
            "modulo_id": str(uuid4()),
            "papel": "EDITAR",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_modulos_api_reatribuicao_atualiza_papel(
    client: httpx.AsyncClient, api_token_paulo: str, manoel_user: User
) -> None:
    """Atribuir de novo o mesmo par (user, módulo) faz UPSERT do papel."""
    h = {"Authorization": f"Bearer {api_token_paulo}"}
    slug = f"upsert-{uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/modulos", headers=h, json={"slug": slug, "nome": "Upsert"}
    )
    assert resp.status_code == 201, resp.text
    modulo_id = resp.json()["id"]

    body = {
        "user_id": str(manoel_user.id),
        "modulo_id": modulo_id,
        "papel": "VISUALIZAR",
    }
    resp = await client.post("/api/v1/modulos/atribuicoes", headers=h, json=body)
    assert resp.status_code == 201, resp.text

    resp = await client.post(
        "/api/v1/modulos/atribuicoes", headers=h, json={**body, "papel": "ADMIN"}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["papel"] == "ADMIN"

    # cleanup
    await client.delete(
        f"/api/v1/modulos/atribuicoes/{manoel_user.id}/{modulo_id}", headers=h
    )
    await client.patch(
        f"/api/v1/modulos/{modulo_id}", headers=h, json={"ativo": False}
    )
