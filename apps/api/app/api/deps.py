"""SINDESTIVA-PE · Dependencies compartilhadas entre routers.

Reexporta `get_db` + `require_user` para ergonomia dos routers.
"""
from __future__ import annotations

from app.core.database import get_db
from app.core.security import require_user

__all__ = ["get_db", "require_user"]
