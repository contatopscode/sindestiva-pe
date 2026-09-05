"""SINDESTIVA-PE · Policy de permissão por módulo (issue #14).

Camada aditiva sobre `app.core.security`. NÃO substitui nem altera
nenhum guard existente (`require_user`, `_require_dirigente` do /bi) —
risco "conflito com middleware de auth já existente" do plano é
mitigado por composição: `requer_modulo()` chama o mesmo
`oauth2_scheme` + `decode_token` que o resto da API usa.

Desenho em 3 camadas:

  1. Funções puras (`nivel_papel`, `papel_satisfaz`, `pode_acessar`) —
     testáveis sem DB e sem FastAPI. Toda a regra vive aqui.
  2. `CachePermissoes` — TTL in-process. Mitiga o risco de performance
     do plano: sem ele, TODA request numa rota protegida faria um JOIN
     users×usuario_modulos×modulos.
  3. `requer_modulo(slug, papel_minimo)` — factory de dependency
     FastAPI que costura 1+2 com o DB.

Fail-closed em todos os pontos: papel desconhecido = nível 0, ausência
de atribuição = sem acesso, role desconhecida = não-superusuário.

Por que cache in-process e não Redis: o volume é ~10 usuários internos
× ~8 módulos. Um dict com TTL de 60s resolve, sem rede no caminho
quente e sem invalidação distribuída pra manter. Quando a API escalar
pra >1 worker, trocar `_CACHE` por Redis (mesmo shape de interface) —
até lá, o TTL curto já limita a janela de staleness entre workers.
"""
from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_id, get_current_user_role, oauth2_scheme
from app.models.enums import ModuloPapelEnum, RoleEnum

# ---------------------------------------------------------------------------
# 1. Regra pura
# ---------------------------------------------------------------------------

# Hierarquia dos papéis. Vive aqui (e não no enum) porque é a ORDEM que
# a policy compara — mudar isto muda o comportamento de autorização, e
# é o que os testes fixam.
NIVEL_PAPEL: dict[ModuloPapelEnum, int] = {
    ModuloPapelEnum.VISUALIZAR: 1,
    ModuloPapelEnum.EDITAR: 2,
    ModuloPapelEnum.ADMIN: 3,
}

# Roles que acessam qualquer módulo sem atribuição explícita.
# DIRIGENTE = Presidente (Josias) + Diretor de Tecnologia (Paulo).
ROLES_SUPERUSUARIO: frozenset[str] = frozenset({RoleEnum.DIRIGENTE.value})

# TTL do cache de permissões (segundos).
CACHE_TTL_SEGUNDOS = 60


def nivel_papel(papel: ModuloPapelEnum | str | None) -> int:
    """Nível numérico do papel. Desconhecido/ausente → 0 (fail-closed)."""
    if papel is None:
        return 0
    try:
        chave = papel if isinstance(papel, ModuloPapelEnum) else ModuloPapelEnum(papel)
    except ValueError:
        return 0
    return NIVEL_PAPEL.get(chave, 0)


def papel_satisfaz(
    papel_usuario: ModuloPapelEnum | str | None,
    papel_minimo: ModuloPapelEnum | str,
) -> bool:
    """True se o papel do usuário alcança o mínimo exigido pela rota."""
    return nivel_papel(papel_usuario) >= nivel_papel(papel_minimo) > 0


def is_superusuario(role: RoleEnum | str | None) -> bool:
    """True se a role bypassa a matriz de módulos (DIRIGENTE)."""
    if role is None:
        return False
    valor = role.value if isinstance(role, RoleEnum) else str(role)
    return valor in ROLES_SUPERUSUARIO


def pode_acessar(
    *,
    role: RoleEnum | str | None,
    atribuicoes: Mapping[str, ModuloPapelEnum | str],
    slug: str,
    papel_minimo: ModuloPapelEnum | str = ModuloPapelEnum.VISUALIZAR,
) -> bool:
    """Decisão de autorização para um módulo.

    `atribuicoes` é o mapa {slug_do_modulo: papel} do usuário — vem do
    cache ou do DB. Superusuário passa direto; qualquer outro precisa
    de atribuição no MÓDULO pedido com papel >= mínimo.
    """
    if is_superusuario(role):
        return True
    return papel_satisfaz(atribuicoes.get(slug), papel_minimo)


# ---------------------------------------------------------------------------
# 2. Cache
# ---------------------------------------------------------------------------


class CachePermissoes:
    """Cache in-process {user_id: {slug: papel}} com TTL.

    Não é thread-safe por design: a API roda num event loop asyncio
    single-threaded, e as operações aqui são todas síncronas e curtas
    (dict get/set), logo não há ponto de await entre leitura e escrita.
    """

    def __init__(self, ttl_segundos: int = CACHE_TTL_SEGUNDOS) -> None:
        self.ttl_segundos = ttl_segundos
        self._dados: dict[str, tuple[float, dict[str, ModuloPapelEnum]]] = {}

    def get(self, user_id: str) -> dict[str, ModuloPapelEnum] | None:
        """Permissões do usuário, ou None se ausente/expirado."""
        entrada = self._dados.get(user_id)
        if entrada is None:
            return None
        gravado_em, permissoes = entrada
        if (time.monotonic() - gravado_em) >= self.ttl_segundos:
            self._dados.pop(user_id, None)
            return None
        return permissoes

    def set(self, user_id: str, permissoes: dict[str, ModuloPapelEnum]) -> None:
        self._dados[user_id] = (time.monotonic(), permissoes)

    def invalidate(self, user_id: str) -> None:
        """Derruba o cache de UM usuário (após conceder/revogar acesso)."""
        self._dados.pop(user_id, None)

    def invalidate_all(self) -> None:
        """Derruba tudo (após editar/desativar um módulo)."""
        self._dados.clear()

    def size(self) -> int:
        return len(self._dados)


# Instância global usada pelas dependencies e pelo service.
_CACHE = CachePermissoes()


def get_cache() -> CachePermissoes:
    """Acessor do cache global (facilita override em teste)."""
    return _CACHE


# ---------------------------------------------------------------------------
# 3. Integração com DB + FastAPI
# ---------------------------------------------------------------------------


async def carregar_permissoes(
    db: AsyncSession, user_id: str, *, usar_cache: bool = True
) -> dict[str, ModuloPapelEnum]:
    """Mapa {slug: papel} do usuário. Só módulos ATIVOS contam.

    Módulo desativado deixa de conceder acesso imediatamente, sem
    precisar apagar as atribuições — reativar devolve tudo.
    """
    if usar_cache:
        em_cache = _CACHE.get(user_id)
        if em_cache is not None:
            return em_cache

    # Import local: evita ciclo `core.permissions` ↔ `models` no boot.
    from app.models.modulos import Modulo, UsuarioModulo  # noqa: PLC0415

    stmt = (
        select(Modulo.slug, UsuarioModulo.papel)
        .join(UsuarioModulo, UsuarioModulo.modulo_id == Modulo.id)
        .where(UsuarioModulo.user_id == user_id, Modulo.ativo.is_(True))
    )
    linhas = await db.execute(stmt)
    permissoes = {slug: papel for slug, papel in linhas.all()}

    if usar_cache:
        _CACHE.set(user_id, permissoes)
    return permissoes


class ContextoModulo:
    """O que a rota protegida recebe: quem é o caller e com que papel."""

    def __init__(
        self,
        *,
        user_id: str,
        role: str | None,
        slug: str,
        papel: ModuloPapelEnum | None,
    ) -> None:
        self.user_id = user_id
        self.role = role
        self.slug = slug
        # Superusuário não tem atribuição explícita — reportamos ADMIN,
        # que é o poder efetivo dele no módulo.
        self.papel = papel or (ModuloPapelEnum.ADMIN if is_superusuario(role) else None)

    @property
    def is_superusuario(self) -> bool:
        return is_superusuario(self.role)


def requer_modulo(
    slug: str,
    papel_minimo: ModuloPapelEnum = ModuloPapelEnum.VISUALIZAR,
):
    """Factory de dependency: bloqueia a rota se faltar permissão no módulo.

    Uso:
        @router.post("/x", dependencies=[Depends(requer_modulo("bi", ModuloPapelEnum.EDITAR))])

        # ou, quando a rota precisa saber o papel:
        async def handler(ctx: ContextoModulo = Depends(requer_modulo("bi"))): ...

    401 se não autenticado, 403 se autenticado sem permissão — mesmo
    formato de erro `{code, message}` que o /bi já usa.
    """

    async def _dependency(
        token: Annotated[str | None, Depends(oauth2_scheme)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> ContextoModulo:
        user_id = get_current_user_id(token=token)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
                headers={"WWW-Authenticate": "Bearer"},
            )
        role = get_current_user_role(token=token)

        if is_superusuario(role):
            return ContextoModulo(user_id=user_id, role=role, slug=slug, papel=None)

        atribuicoes = await carregar_permissoes(db, user_id)
        if not pode_acessar(
            role=role, atribuicoes=atribuicoes, slug=slug, papel_minimo=papel_minimo
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "MODULO_FORBIDDEN",
                    "message": (
                        f"Sem permissão '{papel_minimo.value}' no módulo '{slug}'."
                    ),
                },
            )
        return ContextoModulo(
            user_id=user_id, role=role, slug=slug, papel=atribuicoes.get(slug)
        )

    return _dependency


async def requer_admin_plataforma(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> str:
    """Guard das rotas de administração (CRUD de módulos + matriz).

    Só DIRIGENTE. Mesma semântica do `_require_dirigente` do /bi —
    duplicado de propósito: aquele é local ao BI e pode divergir sem
    quebrar a gestão de acesso.
    """
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = get_current_user_role(token=token)
    if not is_superusuario(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ROLE_REQUIRED",
                "message": f"Administração restrita a DIRIGENTE (você é {role}).",
            },
        )
    return user_id


__all__ = [
    "CACHE_TTL_SEGUNDOS",
    "NIVEL_PAPEL",
    "ROLES_SUPERUSUARIO",
    "CachePermissoes",
    "ContextoModulo",
    "carregar_permissoes",
    "get_cache",
    "is_superusuario",
    "nivel_papel",
    "papel_satisfaz",
    "pode_acessar",
    "requer_admin_plataforma",
    "requer_modulo",
]
