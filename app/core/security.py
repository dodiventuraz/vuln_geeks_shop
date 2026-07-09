"""Keamanan: hashing password, JWT, dan dependency current-user.

P1: SEMUA jalur di sini AMAN (praktik benar). Kelemahan yang disengaja
(md5 tanpa salt di Web-A02-a, JWT alg:none di Web-A08/API-A2) baru ditambahkan di fase
P2/P3 sebagai cabang `if challenges.enabled(...)`.
"""

from __future__ import annotations

import hashlib
import hmac
import random
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.challenges import challenges
from app.core.config import settings
from app.core.db import get_db

# --------------------------------------------------------------------------- #
# Password hashing (AMAN): pbkdf2_sha256 dengan salt per-user.
# Format tersimpan: "pbkdf2_sha256$<iters>$<salt_hex>$<hash_hex>"
# --------------------------------------------------------------------------- #


def hash_password(password: str, *, iterations: int | None = None) -> str:
    if challenges.enabled("web.Web-A02-a"):
        # LAB-VULN: Web-A02-a weak hash (intentional) — md5 tanpa salt (cepat & reversible).
        return "md5$" + hashlib.md5(password.encode("utf-8")).hexdigest()  # noqa: S324
    iters = iterations or settings.pbkdf2_iterations
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return f"pbkdf2_sha256${iters}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    # Verifikasi selalu berdasarkan FORMAT hash tersimpan (bukan toggle saat ini),
    # agar akun lama tetap bisa login setelah toggle diubah.
    if stored.startswith("md5$"):
        return hmac.compare_digest(hashlib.md5(password.encode("utf-8")).hexdigest(), stored[4:])  # noqa: S324
    try:
        algo, iters_s, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iters_s)
    )
    return hmac.compare_digest(dk.hex(), hash_hex)


# --------------------------------------------------------------------------- #
# Token reset password.
# AMAN: secrets (tak terprediksi). Web-A07-b memakai `random` ber-seed publik.
# --------------------------------------------------------------------------- #


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def predictable_reset_token(user_id: int) -> str:
    """LAB-VULN: Web-A07-b — token reset dari `random` ber-seed nilai publik (user id).

    Karena seed diketahui/di-enum, penyerang bisa menghitung token yang sama.
    """
    rng = random.Random(user_id)  # noqa: S311 — sengaja lemah untuk lab
    return f"{rng.randint(100000, 999999):06d}"


def make_reset_token(user_id: int) -> str:
    if challenges.enabled("web.Web-A07-b"):
        return predictable_reset_token(user_id)
    return generate_token()


# --------------------------------------------------------------------------- #
# JWT (AMAN): HS256 + verifikasi tanda tangan + exp.
# --------------------------------------------------------------------------- #


def create_access_token(*, subject: str | int, role: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    # AMAN: pin algoritma & verifikasi tanda tangan.
    # TODO[P3] API-A2 / Web-A08: cabang rentan (terima alg:none / secret lemah) diselipkan di sini.
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# --------------------------------------------------------------------------- #
# Dependency: current user (web session) + role guard.
# --------------------------------------------------------------------------- #


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Ambil user dari session cookie. None bila belum login."""
    from app.models import User  # import lokal untuk hindari siklus

    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_login(user=Depends(get_current_user)):
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Harus login."
        )
    return user


def require_admin(user=Depends(require_login)):
    # AMAN: pengecekan role dipasang. (Web-A01-b/Web-A01-c/API-A5 akan melepas ini secara selektif di P2/P3.)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Butuh hak admin."
        )
    return user


def get_user_by_email(db: Session, email: str) -> Optional[Any]:
    """Lookup user via email — AMAN: query parameterized (ORM).

    Dipakai jalur API (P3) & registrasi. Untuk login web lihat find_user_for_login().
    """
    from app.models import User

    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def find_user_for_login(db: Session, email: str) -> Optional[Any]:
    """Lookup user saat login web.

    Web-A03-a mengontrol apakah query dirakit lewat f-string mentah (SQLi) atau
    parameterized. Cabang rentan memungkinkan payload `' OR '1'='1' -- ` mengembalikan
    baris user meski email tak cocok → dipakai route login untuk mendeteksi bypass.
    """
    from app.models import User

    if challenges.enabled("web.Web-A03-a"):
        # LAB-VULN: Web-A03-a SQLi login (intentional) — input email dirakit mentah ke query.
        sql = text(f"SELECT * FROM users WHERE email = '{email}'")  # noqa: S608
        row = db.execute(sql).first()
        return db.get(User, row.id) if row else None
    # AMAN: parameterized (ORM).
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()
