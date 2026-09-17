"""Testes de CORS (allowlist + preflight)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.cors import build_cors_allow_origins, parse_cors_origins_csv
from app.main import app


def test_builtin_includes_hom_and_prod() -> None:
    origins = build_cors_allow_origins()
    assert "https://web.hom.lousa.pscode.ia.br" in origins
    assert "https://pwa.hom.lousa.pscode.ia.br" in origins
    assert "https://web.lousa.pscode.ia.br" in origins
    assert "http://localhost:3000" in origins


def test_cors_origins_env_unions_with_builtin() -> None:
    extra = "https://preview.example.com,https://web.lousa.pscode.ia.br"
    origins = build_cors_allow_origins(extra)
    assert origins.count("https://web.lousa.pscode.ia.br") == 1
    assert "https://preview.example.com" in origins
    assert "https://web.hom.lousa.pscode.ia.br" in origins


def test_parse_cors_origins_csv() -> None:
    assert parse_cors_origins_csv("") == []
    assert parse_cors_origins_csv("  a , b, ") == ["a", "b"]


def test_preflight_hom_origin() -> None:
    client = TestClient(app)
    resp = client.options(
        "/health",
        headers={
            "Origin": "https://web.hom.lousa.pscode.ia.br",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert (
        resp.headers.get("access-control-allow-origin")
        == "https://web.hom.lousa.pscode.ia.br"
    )
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_preflight_prod_origin() -> None:
    client = TestClient(app)
    resp = client.options(
        "/health",
        headers={
            "Origin": "https://web.lousa.pscode.ia.br",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "https://web.lousa.pscode.ia.br"
