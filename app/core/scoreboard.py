"""Scoreboard sederhana: validasi flag & progres challenge.

Membaca flag dari `challenges.yaml` (via loader) dan mencocokkan submission.
Tidak membocorkan flag — hanya status solved. Progres per-peserta disimpan di
session (mode free-form; bisa direset dengan logout/clear cookie).
"""

from __future__ import annotations

from app.core.challenges import challenges


def flag_to_challenge() -> dict[str, str]:
    """Peta {flag_value: 'section.id'} dari seluruh entri challenges."""
    mapping: dict[str, str] = {}
    for section, entries in challenges._data.items():
        if not isinstance(entries, dict):
            continue
        for cid, meta in entries.items():
            if isinstance(meta, dict) and meta.get("flag"):
                mapping[str(meta["flag"])] = f"{section}.{cid}"
    return mapping


def check_flag(submitted: str) -> str | None:
    """Kembalikan id challenge bila flag benar, atau None."""
    return flag_to_challenge().get((submitted or "").strip())


def all_challenges() -> list[dict]:
    out: list[dict] = []
    for section, entries in challenges._data.items():
        if not isinstance(entries, dict):
            continue
        for cid, meta in entries.items():
            if not isinstance(meta, dict):
                continue
            out.append(
                {
                    "id": f"{section}.{cid}",
                    "section": section,
                    "level": meta.get("level"),
                    "enabled": bool(meta.get("enabled")),
                    "has_flag": bool(meta.get("flag")),
                }
            )
    return out


def total_flags() -> int:
    return sum(1 for c in all_challenges() if c["has_flag"])
