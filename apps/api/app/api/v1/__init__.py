"""SINDESTIVA-PE · v1 routers.

Aggregate router montado em app.main.

Routers expostos:
  - /auth         → login, refresh, me
  - /users        → CRUD users (admin)
  - /lousa        → GET lousa atual, por porto/turno
  - /remanejamentos → POST/GET/PATCH
  - /ogmo         → POST envio de notificação, GET status
  - /auditoria    → GET eventos, POST verificar-hash-chain
  - /health       → health check
"""
from fastapi import APIRouter

from app.api.v1 import (
    auditoria,
    auth,
    health,
    lousa,
    ogmo,
    remanejamentos,
    users,
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(lousa.router)
api_v1_router.include_router(remanejamentos.router)
api_v1_router.include_router(ogmo.router)
api_v1_router.include_router(auditoria.router)

__all__ = ["api_v1_router"]
