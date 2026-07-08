"""Rate limiting login sederhana (in-memory).

Dipakai jalur AMAN W-A07a: setelah beberapa kegagalan login berturut untuk satu
email dalam jendela waktu, akun/permintaan dikunci sementara. Saat W-A07a enabled,
pembatasan ini SENGAJA tidak diberlakukan → brute force bebas.

Catatan lab: state in-memory & tidak terdistribusi — cukup untuk demonstrasi.
"""

from __future__ import annotations

import time

WINDOW_SECONDS = 300  # 5 menit
MAX_FAILURES = 5

_failures: dict[str, list[float]] = {}


def _recent(email: str) -> list[float]:
    now = time.time()
    times = [t for t in _failures.get(email, []) if now - t < WINDOW_SECONDS]
    _failures[email] = times
    return times


def record_failure(email: str) -> None:
    _failures.setdefault(email, []).append(time.time())


def failure_count(email: str) -> int:
    return len(_recent(email))


def is_locked(email: str) -> bool:
    return failure_count(email) >= MAX_FAILURES


def reset(email: str) -> None:
    _failures.pop(email, None)


def clear_all() -> None:
    _failures.clear()
