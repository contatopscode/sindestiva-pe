"""SINDESTIVA-PE · v1 routers.

Aggregate router montado em app.main.

Routers expostos:
  - /health         → health check (sem DB) + DB ping
  - /auth           → login, me, config (T1-08 Sprint 1)
  - /users          → CRUD users (admin)
  - /lousa          → GET lousa atual, por porto/turno, /escalas (Sprint 2)
  - /lousa/public   → GET preview sem auth (Sprint 0 — remover em prod)
  - /scraping       → POST /disparar, GET /status (Sprint 2)
  - /remanejamentos → POST/GET/PATCH
  - /ogmo           → POST envio de notificação, GET status
  - /auditoria      → GET eventos, POST verificar-hash-chain
  - /lgpd           → termo de consentimento + Art. 18 (T1-10 Sprint 1)
"""
from fastapi import APIRouter

from app.api.v1 import (
    auditoria,
    auth,
    health,
    lgpd,
    lousa,
    lousa_public,
    ogmo,
    remanejamentos,
    scraping,
    users,
)

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(lousa.router)
api_v1_router.include_router(lousa_public.router)
api_v1_router.include_router(scraping.router)
api_v1_router.include_router(remanejamentos.router)
api_v1_router.include_router(ogmo.router)
api_v1_router.include_router(auditoria.router)
api_v1_router.include_router(lgpd.router)

__all__ = ["api_v1_router"]
