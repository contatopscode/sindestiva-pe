"""SINDESTIVA-PE · /modulos — gestão de usuários por módulo (issue #14).

Endpoints:
  GET    /modulos                                → módulos do usuário autenticado
  GET    /modulos/todos                          → todos (admin, inclui inativos)
  GET    /modulos/matriz                         → matriz usuários × módulos (admin)
  POST   /modulos                                → cria módulo (admin)
  PATCH  /modulos/{modulo_id}                    → edita/desativa (admin)
  GET    /modulos/{modulo_id}/acesso             → meu papel no módulo (protegida)
  POST   /modulos/atribuicoes                    → concede/atualiza papel (admin)
  DELETE /modulos/atribuicoes/{user}/{modulo}    → revoga papel (admin)

Ordem das rotas importa: `/todos` e `/matriz` são declaradas ANTES de
`/{modulo_id}`, senão o FastAPI casaria "todos" como um UUID inválido
e devolveria 422 em vez de servir a rota.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.core.permissions import (
    ContextoModulo,
    carregar_permissoes,
    get_cache,
    is_superusuario,
    requer_admin_plataforma,
)
from app.core.security import get_current_user_id, get_current_user_role, oauth2_scheme
from app.models.enums import ModuloPapelEnum, RoleEnum
from app.models.modulos import Modulo, UsuarioModulo
from app.models.users import User
from app.schemas.modulo import (
    AcessoModuloOut,
    AtribuicaoCreate,
    AtribuicaoOut,
    MatrizPermissoesResponse,
    ModuloCreate,
    ModuloDoUsuarioOut,
    ModuloOut,
    ModulosDoUsuarioResponse,
    ModulosListResponse,
    ModuloUpdate,
    UsuarioMatrizOut,
)

log = get_logger(__name__)

router = APIRouter(prefix="/modulos", tags=["modulos"])

AdminId = Annotated[str, Depends(requer_admin_plataforma)]
Db = Annotated[AsyncSession, Depends(get_db)]


async def _get_modulo_ou_404(db: AsyncSession, modulo_id: UUID) -> Modulo:
    modulo = await db.get(Modulo, modulo_id)
    if modulo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "MODULO_NOT_FOUND", "message": "Módulo não encontrado."},
        )
    return modulo


# ---------------------------------------------------------------------------
# GET /modulos — módulos do usuário autenticado
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=ModulosDoUsuarioResponse,
    summary="Módulos do usuário autenticado",
)
async def listar_meus_modulos(
    db: Db,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> ModulosDoUsuarioResponse:
    """Só módulos ATIVOS. DIRIGENTE recebe todos (papel efetivo ADMIN)."""
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = get_current_user_role(token=token)

    ativos = (
        await db.execute(
            select(Modulo).where(Modulo.ativo.is_(True)).order_by(Modulo.ordem, Modulo.nome)
        )
    ).scalars().all()

    if is_superusuario(role):
        papeis: dict[str, ModuloPapelEnum] = {
            m.slug: ModuloPapelEnum.ADMIN for m in ativos
        }
    else:
        papeis = await carregar_permissoes(db, user_id)

    items = [
        ModuloDoUsuarioOut(
            id=m.id,
            slug=m.slug,
            nome=m.nome,
            descricao=m.descricao,
            ordem=m.ordem,
            papel=papeis[m.slug],
        )
        for m in ativos
        if m.slug in papeis
    ]
    return ModulosDoUsuarioResponse(items=items, total=len(items))


# ---------------------------------------------------------------------------
# GET /modulos/todos — catálogo completo (admin)
# ---------------------------------------------------------------------------


@router.get(
    "/todos",
    response_model=ModulosListResponse,
    summary="Lista todos os módulos, inclusive inativos (admin)",
)
async def listar_todos_modulos(db: Db, _admin: AdminId) -> ModulosListResponse:
    modulos = (
        await db.execute(select(Modulo).order_by(Modulo.ordem, Modulo.nome))
    ).scalars().all()
    return ModulosListResponse(
        items=[ModuloOut.model_validate(m) for m in modulos], total=len(modulos)
    )


# ---------------------------------------------------------------------------
# GET /modulos/matriz — usuários × módulos (admin)
# ---------------------------------------------------------------------------


@router.get(
    "/matriz",
    response_model=MatrizPermissoesResponse,
    summary="Matriz de permissões: todos os usuários × todos os módulos (admin)",
)
async def matriz_permissoes(db: Db, _admin: AdminId) -> MatrizPermissoesResponse:
    """Uma tela = uma query de módulos + uma de users + uma de vínculos.

    TPAs ficam de fora: são ~2.000 linhas que nunca acessam o Centro de
    Comando e estourariam a tela. A matriz é dos usuários internos.
    """
    modulos = (
        await db.execute(select(Modulo).order_by(Modulo.ordem, Modulo.nome))
    ).scalars().all()

    usuarios = (
        await db.execute(
            select(User)
            .where(User.role != RoleEnum.TPA, User.deleted_at.is_(None))
            .order_by(User.email)
        )
    ).scalars().all()

    vinculos = (
        await db.execute(
            select(UsuarioModulo.user_id, Modulo.slug, UsuarioModulo.papel).join(
                Modulo, Modulo.id == UsuarioModulo.modulo_id
            )
        )
    ).all()

    por_usuario: dict[UUID, dict[str, ModuloPapelEnum]] = {}
    for user_id, slug, papel in vinculos:
        por_usuario.setdefault(user_id, {})[slug] = papel

    linhas = [
        UsuarioMatrizOut(
            id=u.id,
            email=u.email,
            # `fiscal`/`dirigente` são relationships lazy="selectin" —
            # já vêm carregados, sem N+1.
            nome=getattr(u.fiscal, "nome_completo", None)
            or getattr(u.dirigente, "nome_completo", None),
            role=u.role.value,
            status=u.status.value,
            papeis=por_usuario.get(u.id, {}),
        )
        for u in usuarios
    ]

    return MatrizPermissoesResponse(
        modulos=[ModuloOut.model_validate(m) for m in modulos],
        usuarios=linhas,
        total_usuarios=len(linhas),
        total_modulos=len(modulos),
    )


# ---------------------------------------------------------------------------
# POST /modulos — cria (admin)
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=ModuloOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um módulo (admin)",
)
async def criar_modulo(payload: ModuloCreate, db: Db, admin_id: AdminId) -> ModuloOut:
    modulo = Modulo(
        slug=payload.slug,
        nome=payload.nome,
        descricao=payload.descricao,
        ordem=payload.ordem,
        ativo=payload.ativo,
    )
    db.add(modulo)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "MODULO_SLUG_DUPLICADO",
                "message": f"Já existe um módulo com slug '{payload.slug}'.",
            },
        ) from None
    await db.refresh(modulo)
    log.info("modulo.criado", slug=modulo.slug, admin_id=admin_id)
    return ModuloOut.model_validate(modulo)


# ---------------------------------------------------------------------------
# PATCH /modulos/{id} — edita / desativa (admin)
# ---------------------------------------------------------------------------


@router.patch(
    "/{modulo_id}",
    response_model=ModuloOut,
    summary="Edita ou desativa um módulo (admin)",
)
async def atualizar_modulo(
    modulo_id: UUID, payload: ModuloUpdate, db: Db, admin_id: AdminId
) -> ModuloOut:
    modulo = await _get_modulo_ou_404(db, modulo_id)

    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(modulo, campo, valor)
    await db.commit()
    await db.refresh(modulo)

    # Ativar/desativar muda o acesso de TODO mundo — o cache é por
    # usuário e não sabe quais foram afetados, então limpamos geral.
    get_cache().invalidate_all()
    log.info("modulo.atualizado", slug=modulo.slug, ativo=modulo.ativo, admin_id=admin_id)
    return ModuloOut.model_validate(modulo)


# ---------------------------------------------------------------------------
# GET /modulos/{id}/acesso — meu papel no módulo (rota protegida)
# ---------------------------------------------------------------------------


@router.get(
    "/{modulo_id}/acesso",
    response_model=AcessoModuloOut,
    summary="Papel do usuário autenticado no módulo (403 se sem permissão)",
)
async def meu_acesso_no_modulo(
    modulo_id: UUID,
    db: Db,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> AcessoModuloOut:
    """Resolve o módulo pelo id e aplica a policy sobre o slug dele.

    `requer_modulo()` é a forma normal de proteger uma rota, mas ele
    fixa o slug em tempo de import. Aqui o módulo é dinâmico (vem da
    URL), então aplicamos a mesma policy na mão.
    """
    user_id = get_current_user_id(token=token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_REQUIRED", "message": "Autenticação obrigatória."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = get_current_user_role(token=token)
    modulo = await _get_modulo_ou_404(db, modulo_id)

    if is_superusuario(role):
        return AcessoModuloOut(
            modulo_id=modulo.id,
            slug=modulo.slug,
            papel=ModuloPapelEnum.ADMIN,
            superusuario=True,
        )

    papel = (await carregar_permissoes(db, user_id)).get(modulo.slug)
    if papel is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "MODULO_FORBIDDEN",
                "message": f"Sem permissão no módulo '{modulo.slug}'.",
            },
        )
    return AcessoModuloOut(
        modulo_id=modulo.id, slug=modulo.slug, papel=papel, superusuario=False
    )


# ---------------------------------------------------------------------------
# POST /modulos/atribuicoes — concede/atualiza (admin)
# ---------------------------------------------------------------------------


@router.post(
    "/atribuicoes",
    response_model=AtribuicaoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Atribui um usuário a um módulo com papel (admin)",
)
async def atribuir_usuario_a_modulo(
    payload: AtribuicaoCreate, db: Db, admin_id: AdminId
) -> AtribuicaoOut:
    """Upsert por (user_id, modulo_id): reatribuir troca o papel.

    Retorna 201 nos dois casos — a operação é idempotente do ponto de
    vista do cliente ("garanta que este user tem este papel").
    """
    await _get_modulo_ou_404(db, payload.modulo_id)

    if await db.get(User, payload.user_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "Usuário não encontrado."},
        )

    existente = (
        await db.execute(
            select(UsuarioModulo).where(
                UsuarioModulo.user_id == payload.user_id,
                UsuarioModulo.modulo_id == payload.modulo_id,
            )
        )
    ).scalar_one_or_none()

    if existente is not None:
        existente.papel = payload.papel
        existente.concedido_por = UUID(admin_id)
        vinculo = existente
    else:
        vinculo = UsuarioModulo(
            user_id=payload.user_id,
            modulo_id=payload.modulo_id,
            papel=payload.papel,
            concedido_por=UUID(admin_id),
        )
        db.add(vinculo)

    await db.commit()
    await db.refresh(vinculo)

    # Critério de aceite: a mudança vale na hora, sem esperar o TTL.
    get_cache().invalidate(str(payload.user_id))
    log.info(
        "modulo.atribuido",
        user_id=str(payload.user_id),
        modulo_id=str(payload.modulo_id),
        papel=payload.papel.value,
        admin_id=admin_id,
    )
    return AtribuicaoOut.model_validate(vinculo)


# ---------------------------------------------------------------------------
# DELETE /modulos/atribuicoes/{user}/{modulo} — revoga (admin)
# ---------------------------------------------------------------------------


@router.delete(
    "/atribuicoes/{user_id}/{modulo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoga o acesso de um usuário a um módulo (admin)",
)
async def revogar_atribuicao(
    user_id: UUID, modulo_id: UUID, db: Db, admin_id: AdminId
) -> Response:
    vinculo = (
        await db.execute(
            select(UsuarioModulo).where(
                UsuarioModulo.user_id == user_id,
                UsuarioModulo.modulo_id == modulo_id,
            )
        )
    ).scalar_one_or_none()
    if vinculo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ATRIBUICAO_NOT_FOUND",
                "message": "Atribuição não encontrada.",
            },
        )

    await db.delete(vinculo)
    await db.commit()

    get_cache().invalidate(str(user_id))
    log.info(
        "modulo.revogado",
        user_id=str(user_id),
        modulo_id=str(modulo_id),
        admin_id=admin_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
