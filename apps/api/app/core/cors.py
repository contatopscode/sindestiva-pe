"""SINDESTIVA-PE · CORS allowlist (browser → API).

Origins fixos cobrem dev local, Vercel (preview + prod temporário), produção
(`*.lousa.pscode.ia.br`) e homologação (`*.hom.lousa.pscode.ia.br`).

`CORS_ORIGINS` no `.env` / Coolify **adiciona** entradas (union), não substitui
a lista base — evita quebrar deploy se só hom for listado no painel.
"""

from __future__ import annotations

# Regex única aceita pelo CORSMiddleware (previews Vercel).
CORS_ALLOW_ORIGIN_REGEX = r"https://sindestiva-(web|pwa)[a-z0-9-]*\.vercel\.app"

_BUILTIN_CORS_ORIGINS: tuple[str, ...] = (
    # Dev (Next.js web + pwa)
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3010",
    "http://127.0.0.1:3010",
    # Vercel temporário (Sprint 0+)
    "https://sindestiva-web.vercel.app",
    "https://sindestiva-pwa.vercel.app",
    # Produção (Coolify / DNS custom)
    "https://web.lousa.pscode.ia.br",
    "https://pwa.lousa.pscode.ia.br",
    "https://api.lousa.pscode.ia.br",
    # Homologação (branch homolog · Coolify HOM)
    "https://web.hom.lousa.pscode.ia.br",
    "https://pwa.hom.lousa.pscode.ia.br",
    "https://api.hom.lousa.pscode.ia.br",
)


def parse_cors_origins_csv(value: str) -> list[str]:
    """Separa `CORS_ORIGINS` por vírgula; ignora vazios."""
    if not value or not value.strip():
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def build_cors_allow_origins(extra_csv: str = "") -> list[str]:
    """Lista final para `CORSMiddleware.allow_origins` (ordem estável, sem dupes)."""
    merged: list[str] = list(_BUILTIN_CORS_ORIGINS)
    for origin in parse_cors_origins_csv(extra_csv):
        if origin not in merged:
            merged.append(origin)
    return merged
