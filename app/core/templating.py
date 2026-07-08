"""Instance Jinja2Templates bersama + konteks global.

Autoescape Jinja2 AKTIF (default) — ini jalur AMAN P1. Titik XSS/SSTI (W-A03b/W-A03c)
baru dibuka di fase P2 dengan `| safe` / render string dinamis, dijaga challenges flag.
"""

from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app.core.challenges import challenges
from app.core.config import settings
from app.core.thumbs import product_thumbnail

templates = Jinja2Templates(directory=settings.templates_dir)

# Konteks global untuk semua template (banner lab wajib tampil — REQ-S2).
templates.env.globals["LAB_WARNING"] = settings.lab_warning
templates.env.globals["APP_NAME"] = settings.app_name
# Dipakai template untuk bercabang rentan/aman (mis. W-A03b XSS `| safe`).
templates.env.globals["challenges"] = challenges
# Thumbnail dummy per produk (inline SVG) saat belum ada gambar.
templates.env.globals["product_thumbnail"] = product_thumbnail
