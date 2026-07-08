"""API auth (v1) — penerbitan JWT untuk jalur API (PyJWT).

P1: hanya penerbitan token yang AMAN. Permukaan API penuh (BOLA, mass assignment,
dll.) dibangun di fase P3. Verifikasi token yang RENTAN (A-2 alg:none) juga menyusul.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import create_access_token, get_user_by_email, verify_password
from app.schemas import LoginIn, Token

router = APIRouter(prefix="/api/v1/auth", tags=["api-auth"])


@router.post("/token", response_model=Token)
def issue_token(payload: LoginIn, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Kredensial tidak valid."
        )
    token = create_access_token(subject=user.id, role=user.role)
    return Token(access_token=token)
