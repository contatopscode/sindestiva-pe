"""SINDESTIVA-PE · Hash chain (SHA-256) — ADR-005.

Implementação canônica SHA-256 com:
  - JSON canônico (sort_keys=True, separators) — essencial pra
    reproducibilidade
  - Encadeamento: `hash_evento = SHA256(payload_canonico + hash_anterior)`
  - Genesis hash = "0" * 64

TODO(D8): hoje a cadeia é paralela em `remanejamentos.hash_evento`. O
DD recomenda (a) cadeia única global em `audit_events`. Esta
implementação já trata isso (a função `compute_hash` recebe o
`hash_anterior` como entrada), mas o ponto de uso precisa ser
revisitado: preferir `AuditEvent.hash_anterior` sobre
`Remanejamento.hash_anterior_id`.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

# Genesis hash — usado como `hash_anterior` do primeiro evento.
GENESIS_HASH = "0" * 64


def _canonical_json(payload: dict[str, Any]) -> str:
    """JSON canônico: sort_keys + separadores estáveis (RFC 8785-ish)."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,  # datetimes viram ISO via __str__
    )


def compute_hash(previous_hash: str, payload: dict[str, Any]) -> str:
    """Calcula SHA-256 de `payload_canonico + previous_hash`.

    Args:
        previous_hash: hash do evento anterior (ou GENESIS_HASH).
        payload: dict serializável em JSON.

    Returns:
        Hash SHA-256 em hex (64 chars).
    """
    canonical = _canonical_json(payload)
    h = hashlib.sha256()
    h.update(previous_hash.encode("utf-8"))
    h.update(b"|")
    h.update(canonical.encode("utf-8"))
    return h.hexdigest()


def verify_chain(
    events: list[Any],
    *,
    hash_field: str = "hash_evento",
    previous_field: str = "hash_anterior",
    sequencia_field: str = "sequencia",
) -> tuple[bool, int]:
    """Verifica integridade de uma cadeia de eventos.

    Args:
        events: lista de objetos com `hash_evento`, `hash_anterior` (ou
            `sequencia` para ordenação) e `payload_after`/`payload_before`.
        hash_field: nome do atributo que contém o hash do evento.
        previous_field: nome do atributo que contém o hash anterior.
        sequencia_field: nome do atributo de sequência (ordenação).

    Returns:
        Tupla `(integro, indice_primeiro_erro)`. Se íntegro,
        `indice_primeiro_erro = -1`. Se houver quebra, índice do
        primeiro evento que não confere.
    """
    if not events:
        return True, -1

    # Ordenar por sequência (se existir) para garantir cadeia linear.
    sorted_events = sorted(events, key=lambda e: getattr(e, sequencia_field))

    expected_previous = GENESIS_HASH
    for idx, ev in enumerate(sorted_events):
        actual_previous = getattr(ev, previous_field, None) or GENESIS_HASH
        if actual_previous != expected_previous:
            return False, idx
        # Recalcula hash do evento (precisa dos mesmos campos do payload
        # que foram usados na criação; aqui usamos payload_after como
        # aproximação canônica).
        payload = getattr(ev, "payload_after", None)
        if payload is None:
            return False, idx
        recalculated = compute_hash(actual_previous, payload)
        if recalculated != getattr(ev, hash_field):
            return False, idx
        expected_previous = recalculated
    return True, -1


__all__ = [
    "GENESIS_HASH",
    "compute_hash",
    "verify_chain",
]
