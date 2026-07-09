"""State klaim promo per-user (in-memory) — dipakai API-A6 (business flow abuse).

- AMAN (API-A6 disabled): kuota 1 klaim per user.
- RENTAN (API-A6 enabled): tanpa kuota → bisa diborong/di-spam via API.

State in-memory (cukup untuk lab & test; di-clear per test lewat conftest).
"""

from __future__ import annotations

_claims: dict[int, int] = {}


def claim_count(user_id: int) -> int:
    return _claims.get(user_id, 0)


def add_claim(user_id: int) -> int:
    _claims[user_id] = _claims.get(user_id, 0) + 1
    return _claims[user_id]


def clear() -> None:
    _claims.clear()
