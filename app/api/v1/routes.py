"""REST API v1 — permukaan LAMA & lebih rentan.

Kerentanan (toggle via challenges.yaml):
- A-1  BOLA: GET /api/v1/orders/{id} tanpa cek kepemilikan.
- A-2  Broken Auth: dependency v1 menerima JWT tak terverifikasi (lihat api/deps.py).
- A-3b Excessive Data Exposure: GET /api/v1/users/{id} mengembalikan schema penuh.
- A-9  Improper Inventory: endpoint lawas tak terdokumentasi `/api/v1/_debug/orders`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_api_user_v1
from app.api.serializers import order_dict, user_full, user_public
from app.core.challenges import challenges
from app.core.db import get_db
from app.models import Order, User

router = APIRouter(prefix="/api/v1", tags=["api-v1"])


@router.get("/me")
def me_v1(request: Request, current: User = Depends(get_api_user_v1)):
    data = user_public(current)
    # A-2: bila token diterima lewat jalur tak-terverifikasi → bukti broken auth.
    if challenges.enabled("api.A-2") and getattr(request.state, "jwt_forged", False):
        data["flag"] = challenges.flag("api.A-2")
    return data


@router.get("/users/{user_id}")
def get_user_v1(user_id: int, current: User = Depends(get_api_user_v1), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan.")
    if challenges.enabled("api.A-3b"):
        # LAB-VULN: A-3b (intentional) — kembalikan schema penuh (bocor password_hash/PII).
        data = user_full(user)
        data["flag"] = challenges.flag("api.A-3b")
        return data
    return user_public(user)


@router.get("/orders")
def list_orders_v1(current: User = Depends(get_api_user_v1), db: Session = Depends(get_db)):
    orders = db.execute(select(Order).where(Order.user_id == current.id)).scalars().all()
    return [order_dict(o) for o in orders]


@router.get("/orders/{order_id}")
def get_order_v1(order_id: int, current: User = Depends(get_api_user_v1), db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order tidak ditemukan.")
    if challenges.enabled("api.A-1"):
        # LAB-VULN: A-1 BOLA (intentional) — akses object by id TANPA cek kepemilikan.
        data = order_dict(order)
        if order.user_id != current.id:
            data["flag"] = challenges.flag("api.A-1")
        return data
    # AMAN: hanya order milik pemanggil.
    if order.user_id != current.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order tidak ditemukan.")
    return order_dict(order)


@router.get("/_debug/orders", include_in_schema=False)
def debug_orders_v1(current: User = Depends(get_api_user_v1), db: Session = Depends(get_db)):
    # LAB-VULN: A-9 (intentional) — endpoint lawas TAK TERDOKUMENTASI, dump semua order.
    if not challenges.enabled("api.A-9"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    orders = db.execute(select(Order)).scalars().all()
    return {"flag": challenges.flag("api.A-9"), "orders": [order_dict(o) for o in orders]}
