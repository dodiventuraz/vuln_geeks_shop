"""Penyajian file statis "assets" — target Web-A05-b.

- AMAN (disabled): tolak path traversal & dotfile; hanya file biasa di dalam
  direktori `lab_files/`.
- RENTAN (Web-A05-b enabled): sajikan path apa adanya → dotfile (`.env.bak`),
  artefak `.bak`, dan path traversal (`../`) ikut terlayani.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.core.challenges import challenges

BASE = Path(__file__).resolve().parents[2] / "lab_files"

router = APIRouter(tags=["web-files"])


@router.get("/assets/{path:path}", response_class=PlainTextResponse)
def serve_asset(path: str):
    if challenges.enabled("web.Web-A05-b"):
        # LAB-VULN: Web-A05-b (intentional) — tanpa sanitasi: dotfile & traversal terlayani.
        target = BASE / path
    else:
        # AMAN: tolak dotfile & traversal; batasi ke dalam BASE.
        parts = Path(path).parts
        if any(p == ".." or p.startswith(".") for p in parts):
            raise HTTPException(status_code=404)
        target = BASE / path
        try:
            target.resolve().relative_to(BASE.resolve())
        except ValueError:
            raise HTTPException(status_code=404)

    if not target.is_file():
        raise HTTPException(status_code=404)
    return PlainTextResponse(target.read_text(encoding="utf-8", errors="replace"))
