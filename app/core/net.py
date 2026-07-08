"""Utilitas jaringan untuk fitur "import produk dari URL".

P1: implementasi AMAN — memvalidasi tujuan agar server tidak bisa dipaksa
menembak alamat internal (anti-SSRF). Versi RENTAN (W-A10 / A-7) baru ditambahkan
di fase P2/P3 sebagai cabang `if challenges.enabled(...)`.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx


class UnsafeUrlError(ValueError):
    """URL ditolak karena mengarah ke tujuan yang tidak diizinkan."""


def _is_public_ip(host: str) -> bool:
    """True hanya bila SEMUA hasil resolusi DNS host adalah IP publik."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True


def validate_public_url(url: str) -> str:
    """Validasi URL: hanya http/https ke host yang resolve ke IP publik.

    Mengembalikan URL bila aman, atau melempar UnsafeUrlError.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("Skema URL harus http atau https.")
    if not parsed.hostname:
        raise UnsafeUrlError("URL tidak memiliki host.")
    if not _is_public_ip(parsed.hostname):
        raise UnsafeUrlError("Tujuan mengarah ke alamat internal/non-publik — ditolak.")
    return url


def fetch_bytes(url: str, *, max_bytes: int = 5 * 1024 * 1024, timeout: float = 5.0) -> bytes:
    """Ambil konten URL dengan batas ukuran & timeout.

    AMAN: validasi tujuan dulu, larang redirect (agar tidak di-bypass ke internal).
    TODO[P2/P3] W-A10 / A-7: cabang rentan (httpx.get(user_url) tanpa validasi)
    diselipkan di call-site (web/admin & api), dijaga challenges.enabled(...).
    """
    validate_public_url(url)
    with httpx.Client(follow_redirects=False, timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
        content = resp.content
        if len(content) > max_bytes:
            raise UnsafeUrlError("Konten melebihi batas ukuran.")
        return content


def fetch_url_unsafe(
    url: str, *, max_bytes: int = 5 * 1024 * 1024, timeout: float = 5.0
) -> tuple[str, bytes]:
    """LAB-VULN: W-A10 SSRF (intentional) — ambil URL TANPA validasi tujuan.

    Mengikuti redirect dan menembak alamat mana pun (termasuk internal/loopback).
    Mengembalikan (preview_text, content). Dipakai hanya di cabang challenge enabled.
    """
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        resp = client.get(url)  # noqa: S113 — timeout diberikan; tanpa validasi tujuan (disengaja)
        content = resp.content[:max_bytes]
        return resp.text[:2000], content
