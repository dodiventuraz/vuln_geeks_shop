"""Loader `challenges.yaml` — mekanisme toggle kerentanan.

Kontrak (CLAUDE.md §7): setiap kerentanan bisa dinyalakan/dimatikan, dan kode
bercabang berdasarkan flag lewat `challenges.enabled("web.W-A03a")`.

P0: hanya mekanismenya. Semua entri masih `enabled: false` dan belum ada
cabang kode rentan yang membacanya.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.config import settings


class Challenges:
    """Wrapper tipis di atas isi `challenges.yaml`.

    Lookup memakai path bertitik, mis. `enabled("web.W-A03a")` membaca
    `web -> W-A03a -> enabled`.
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data or {}

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Challenges":
        file_path = Path(path or settings.challenges_file)
        if not file_path.exists():
            return cls({})
        with file_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(f"challenges file harus berupa mapping, dapat: {type(data)!r}")
        return cls(data)

    def _get(self, dotted_key: str) -> dict[str, Any] | None:
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node if isinstance(node, dict) else None

    def enabled(self, dotted_key: str) -> bool:
        """True hanya bila entri ada dan `enabled: true`."""
        entry = self._get(dotted_key)
        return bool(entry and entry.get("enabled") is True)

    def level(self, dotted_key: str) -> str | None:
        entry = self._get(dotted_key)
        return entry.get("level") if entry else None

    def flag(self, dotted_key: str) -> str | None:
        entry = self._get(dotted_key)
        return entry.get("flag") if entry else None

    def reload(self, path: str | Path | None = None) -> None:
        self._data = Challenges.load(path)._data


# Instance modul-level yang dipakai lintas aplikasi.
challenges = Challenges.load()
