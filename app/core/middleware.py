"""Middleware dasar lab.

`LabWarningMiddleware` menambahkan response header `X-Lab-Warning` ke setiap
respons (REQ-S2 / CLAUDE.md §2.4). Banner UI ditangani terpisah di layer web.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.challenges import challenges
from app.core.config import settings


class LabWarningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Lab-Warning"] = settings.lab_warning_header
        return response


class CorsSecurityMiddleware(BaseHTTPMiddleware):
    """CORS + security headers, bercabang di W-A05c.

    - AMAN (disabled): hanya origin ter-allowlist yang di-ACAO, plus security header
      dipasang (nosniff / frame-options / referrer-policy).
    - RENTAN (W-A05c enabled): refleksikan Origin APA PUN + `allow-credentials: true`,
      dan security header TIDAK dipasang.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        origin = request.headers.get("origin")

        if challenges.enabled("web.W-A05c"):
            # LAB-VULN: W-A05c (intentional) — wildcard-refleksi origin + credentials.
            if origin:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                # Bukti: origin sembarang bisa membaca respons ber-kredensial.
                response.headers["X-Lab-Flag"] = challenges.flag("web.W-A05c") or ""
            # security header sengaja TIDAK dipasang.
        else:
            # AMAN: hanya origin ter-allowlist.
            if origin and origin in settings.cors_allow_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response
