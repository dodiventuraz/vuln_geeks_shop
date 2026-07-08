"""Penyimpanan file upload (avatar & gambar produk) — AMAN di P1.

Menyimpan ke `settings.upload_dir` dengan nama acak + ekstensi ter-allowlist.
Path traversal & eksekusi tidak dimungkinkan karena nama file dibuat server.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings

_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _upload_root() -> Path:
    root = Path(settings.upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_upload(file: UploadFile, *, prefix: str = "img") -> str:
    """Simpan file dan kembalikan path relatif untuk disimpan di DB (mis. 'uploads/xxx.png')."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise ValueError("Tipe file tidak diizinkan.")
    name = f"{prefix}_{secrets.token_hex(8)}{ext}"
    dest = _upload_root() / name
    with dest.open("wb") as fh:
        fh.write(file.file.read())
    return f"uploads/{name}"


def save_bytes(data: bytes, *, ext: str = ".png", prefix: str = "img") -> str:
    if ext.lower() not in _ALLOWED_EXT:
        ext = ".png"
    name = f"{prefix}_{secrets.token_hex(8)}{ext.lower()}"
    dest = _upload_root() / name
    with dest.open("wb") as fh:
        fh.write(data)
    return f"uploads/{name}"
