"""Dependency bersama untuk REST API (auth Bearer JWT).

Dua varian current-user:
- `get_api_user_v1`: permukaan LAMA, lebih rentan. Bercabang di API-A2 (Broken Auth):
  saat enabled, token yang tak tervalidasi (mis. `alg:none` / tanda tangan palsu)
  tetap diterima.
- `get_api_user_v2`: permukaan BARU, selalu verifikasi tanda tangan (aman).

Perbedaan v1 vs v2 sekaligus menjadi bahan API-A9 (Improper Inventory Management).
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.challenges import challenges
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Token tidak valid.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _load_user(db: Session, payload: dict) -> User:
    sub = payload.get("sub")
    if sub is None:
        raise _unauthorized()
    user = db.get(User, int(sub))
    if user is None:
        raise _unauthorized("User tidak ditemukan.")
    return user


def get_api_user_v1(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise _unauthorized("Butuh Bearer token.")
    token = creds.credentials
    request.state.jwt_forged = False

    if challenges.enabled("api.API-A2"):
        try:
            payload = decode_access_token(token)  # coba jalur aman dulu
        except jwt.PyJWTError:
            # LAB-VULN: API-A2 (intentional) — terima token TANPA verifikasi tanda tangan
            # (alg:none / secret salah). Klaim dipercaya mentah.
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
            except jwt.PyJWTError as exc:
                raise _unauthorized() from exc
            request.state.jwt_forged = True
    else:
        try:
            payload = decode_access_token(token)  # AMAN: verifikasi tanda tangan + exp
        except jwt.PyJWTError as exc:
            raise _unauthorized() from exc

    return _load_user(db, payload)


def get_api_user_v2(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise _unauthorized("Butuh Bearer token.")
    try:
        payload = decode_access_token(creds.credentials)  # AMAN: selalu verifikasi
    except jwt.PyJWTError as exc:
        raise _unauthorized() from exc
    return _load_user(db, payload)
