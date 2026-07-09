"""FastAPI app — titik masuk Vuln Geeks Shop.

P1 (Fitur e-commerce): fitur FUNGSIONAL & AMAN. Belum ada kerentanan — itu
ditambahkan di P2 (web) / P3 (API). Router web + API-auth di-mount di sini.
"""

from __future__ import annotations

import platform
import traceback
from contextlib import asynccontextmanager
from html import escape
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.core.challenges import challenges
from app.core.config import settings
from app.core.db import Base, engine
from app.core.middleware import CorsSecurityMiddleware, LabWarningMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Lab: buat tabel bila belum ada (Alembic opsional). Idempoten.
    import app.models  # noqa: F401 — daftarkan model ke metadata

    try:
        Base.metadata.create_all(bind=engine)
    except Exception:  # noqa: BLE001 — biarkan app hidup meski DB belum siap (dicek di /health)
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
    description=(
        "⚠️ INTENTIONALLY VULNERABLE — LAB USE ONLY. "
        "Aplikasi latihan pentest non-produksi. Jangan deploy ke jaringan publik."
    ),
)

# --- Middleware (urutan: header lab terluar → CORS/security → session) ---
app.add_middleware(LabWarningMiddleware)
# CORS + security headers. Bercabang di Web-A05-c (lihat CorsSecurityMiddleware).
app.add_middleware(CorsSecurityMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,
)


# --- Exception handler: verbose vs generic (target Web-A05-a) ---
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if challenges.enabled("web.Web-A05-a"):
        # LAB-VULN: Web-A05-a verbose error/debug (intentional) — bocorkan traceback & detail internal.
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        detail = (
            f"{type(exc).__name__}: {exc}\n\n{tb}\n"
            f"python={platform.python_version()}\n"
            f"database_url={settings.database_url}\n"
            f"internal-token={challenges.flag('web.Web-A05-a')}"
        )
        return HTMLResponse(
            f"<h1>500 Internal Server Error</h1><pre>{escape(detail)}</pre>", status_code=500
        )
    # AMAN: pesan generik, detail hanya di log server.
    return HTMLResponse(
        "<h1>500 Internal Server Error</h1><p>Terjadi kesalahan. Silakan coba lagi.</p>",
        status_code=500,
    )

# --- Static & uploads ---
Path(settings.static_dir).mkdir(parents=True, exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
# image_path tersimpan sebagai "uploads/xxx.png" → URL "/uploads/xxx.png".
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


# --- Routers ---
from app.api.v1 import auth as api_auth  # noqa: E402
from app.api.v1 import routes as api_v1  # noqa: E402
from app.api.v2 import routes as api_v2  # noqa: E402
from app.web import admin as web_admin  # noqa: E402
from app.web import auth as web_auth  # noqa: E402
from app.web import cart as web_cart  # noqa: E402
from app.web import files as web_files  # noqa: E402
from app.web import orders as web_orders  # noqa: E402
from app.web import profile as web_profile  # noqa: E402
from app.web import scoreboard as web_scoreboard  # noqa: E402
from app.web import shop as web_shop  # noqa: E402

app.include_router(web_auth.router)
app.include_router(web_shop.router)
app.include_router(web_cart.router)
app.include_router(web_orders.router)
app.include_router(web_profile.router)
app.include_router(web_admin.router)
app.include_router(web_scoreboard.router)
app.include_router(web_files.router)
app.include_router(api_auth.router)
app.include_router(api_v1.router)
app.include_router(api_v2.router)


@app.get("/debug/error", tags=["debug"])
def debug_error():
    """Endpoint pemicu error tak tertangani (untuk mendemokan Web-A05-a)."""
    raise RuntimeError("boom: contoh error tak tertangani untuk lab")


@app.get("/debug/deps", tags=["debug"])
def debug_deps():
    """Ungkap versi dependensi (target Web-A06).

    Saat enabled, bocorkan daftar versi paket (memudahkan fingerprint komponen
    ber-CVE seperti Jinja2). Saat disabled → 404.
    """
    if not challenges.enabled("web.Web-A06"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    pkgs = {}
    for name in ("jinja2", "fastapi", "sqlalchemy", "pyjwt", "python-multipart"):
        try:
            pkgs[name] = version(name)
        except PackageNotFoundError:
            pkgs[name] = None
    # LAB-VULN: Web-A06 — disclosure versi komponen (ber-CVE) + flag.
    return JSONResponse({"dependencies": pkgs, "flag": challenges.flag("web.Web-A06")})


@app.get("/health", tags=["ops"])
def health() -> dict:
    """Cek liveness app + koneksi DB."""
    db_ok = True
    db_error: str | None = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — lab health check, laporkan apa adanya
        db_ok = False
        db_error = str(exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.app_name,
        "version": __version__,
        "env": settings.app_env,
        "warning": settings.lab_warning,
        "database": {"ok": db_ok, "error": db_error},
        "challenges_loaded": bool(challenges._data),
    }
