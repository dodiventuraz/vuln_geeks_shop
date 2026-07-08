"""REST API v2 — permukaan BARU & lebih aman.

Padanan aman dari endpoint v1: verifikasi JWT ketat, cek kepemilikan object,
dan response field terbatas. Kontras v1/v2 = bahan A-9 (Improper Inventory).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_api_user_v2
from app.api.serializers import order_dict, user_public
from app.core.db import get_db
from app.models import Order, User

router = APIRouter(prefix="/api/v2", tags=["api-v2"])


@router.get("/me")
def me_v2(current: User = Depends(get_api_user_v2)):
    return user_public(current)


@router.get("/users/{user_id}")
def get_user_v2(user_id: int, current: User = Depends(get_api_user_v2), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan.")
    # AMAN: field terbatas (tanpa password_hash/PII).
    return user_public(user)


@router.get("/orders/{order_id}")
def get_order_v2(order_id: int, current: User = Depends(get_api_user_v2), db: Session = Depends(get_db)):
    # AMAN: otorisasi object-level (cocokkan pemilik).
    order = db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current.id)
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order tidak ditemukan.")
    return order_dict(order)
