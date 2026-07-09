"""REST API v2 — permukaan BARU & lebih aman.

Padanan aman dari endpoint v1: verifikasi JWT ketat, cek kepemilikan object,
dan response field terbatas. Kontras v1/v2 = bahan API-A9 (Improper Inventory).
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_api_user_v2
from app.api.serializers import order_dict, product_public, user_public
from app.core.net import UnsafeUrlError, fetch_bytes
from app.core.db import get_db
from app.models import Order, Product, User

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


# --- Padanan AMAN dari endpoint v1 yang rentan ---
@router.patch("/user")
def patch_user_v2(
    payload: dict = Body(...),
    current: User = Depends(get_api_user_v2),
    db: Session = Depends(get_db),
):
    # AMAN: allowlist field (tak ada mass assignment ke role/balance/verified).
    for key in ("name", "email"):
        if key in payload:
            setattr(current, key, payload[key])
    db.commit()
    return user_public(current)


@router.get("/products")
def list_products_v2(
    limit: int = 20,
    current: User = Depends(get_api_user_v2),
    db: Session = Depends(get_db),
):
    # AMAN: batasi ukuran halaman.
    effective = max(1, min(limit, 100))
    products = db.execute(select(Product).order_by(Product.id)).scalars().all()
    items = [product_public(p) for p in products[:effective]]
    return {"limit_requested": limit, "limit_effective": effective, "count": len(items), "items": items}


@router.post("/admin/users/{user_id}/role")
def admin_set_role_v2(
    user_id: int,
    payload: dict = Body(...),
    current: User = Depends(get_api_user_v2),
    db: Session = Depends(get_db),
):
    # AMAN: cek peran dipasang.
    if current.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Butuh hak admin.")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan.")
    role = payload.get("role")
    if role in {"guest", "customer", "admin"}:
        target.role = role
        db.commit()
    return {"id": target.id, "role": target.role}


@router.post("/fetch-url")
def fetch_url_v2(payload: dict = Body(...), current: User = Depends(get_api_user_v2)):
    # AMAN: validasi tujuan (anti-SSRF).
    url = str(payload.get("url", ""))
    try:
        content = fetch_bytes(url)
    except (UnsafeUrlError, Exception) as exc:  # noqa: BLE001 — lab
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"url": url, "bytes": len(content)}
