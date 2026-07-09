"""REST API v1 — permukaan LAMA & lebih rentan.

Kerentanan (toggle via challenges.yaml):
- API-A1  BOLA: GET /api/v1/orders/{id} tanpa cek kepemilikan.
- API-A2  Broken Auth: dependency v1 menerima JWT tak terverifikasi (lihat api/deps.py).
- API-A3-b Excessive Data Exposure: GET /api/v1/users/{id} mengembalikan schema penuh.
- API-A9  Improper Inventory: endpoint lawas tak terdokumentasi `/api/v1/_debug/orders`.
"""

from __future__ import annotations

import platform

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_api_user_v1
from app.api.serializers import order_dict, product_public, user_full, user_public
from app.core import payments, promo
from app.core.challenges import challenges
from app.core.config import settings
from app.core.db import get_db
from app.core.net import UnsafeUrlError, fetch_bytes, fetch_url_unsafe
from app.models import Order, Product, User

router = APIRouter(prefix="/api/v1", tags=["api-v1"])

_PRIVILEGED_FIELDS = {"role", "balance", "is_verified", "password_hash", "id"}


@router.get("/me")
def me_v1(request: Request, current: User = Depends(get_api_user_v1)):
    data = user_public(current)
    # API-A2: bila token diterima lewat jalur tak-terverifikasi → bukti broken auth.
    if challenges.enabled("api.API-A2") and getattr(request.state, "jwt_forged", False):
        data["flag"] = challenges.flag("api.API-A2")
    return data


@router.get("/users/{user_id}")
def get_user_v1(user_id: int, current: User = Depends(get_api_user_v1), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan.")
    if challenges.enabled("api.API-A3-b"):
        # LAB-VULN: API-A3-b (intentional) — kembalikan schema penuh (bocor password_hash/PII).
        data = user_full(user)
        data["flag"] = challenges.flag("api.API-A3-b")
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
    if challenges.enabled("api.API-A1"):
        # LAB-VULN: API-A1 BOLA (intentional) — akses object by id TANPA cek kepemilikan.
        data = order_dict(order)
        if order.user_id != current.id:
            data["flag"] = challenges.flag("api.API-A1")
        return data
    # AMAN: hanya order milik pemanggil.
    if order.user_id != current.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order tidak ditemukan.")
    return order_dict(order)


@router.get("/_debug/orders", include_in_schema=False)
def debug_orders_v1(current: User = Depends(get_api_user_v1), db: Session = Depends(get_db)):
    # LAB-VULN: API-A9 (intentional) — endpoint lawas TAK TERDOKUMENTASI, dump semua order.
    if not challenges.enabled("api.API-A9"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    orders = db.execute(select(Order)).scalars().all()
    return {"flag": challenges.flag("api.API-A9"), "orders": [order_dict(o) for o in orders]}


# --------------------------------------------------------------------------- #
# API-A3-a · Mass Assignment (PATCH /api/v1/user)
# --------------------------------------------------------------------------- #
@router.patch("/user")
def patch_user_v1(
    payload: dict = Body(...),
    current: User = Depends(get_api_user_v1),
    db: Session = Depends(get_db),
):
    columns = set(User.__table__.columns.keys())
    if challenges.enabled("api.API-A3-a"):
        # LAB-VULN: API-A3-a mass assignment (intentional) — bind payload mentah ke model,
        # termasuk field istimewa (role/balance/is_verified).
        touched_privileged = False
        for key, value in payload.items():
            if key in columns:
                setattr(current, key, value)
                if key in _PRIVILEGED_FIELDS:
                    touched_privileged = True
        db.commit()
        data = user_full(current)
        if touched_privileged:
            data["flag"] = challenges.flag("api.API-A3-a")
        return data
    # AMAN: allowlist field yang boleh diubah user.
    for key in ("name", "email"):
        if key in payload:
            setattr(current, key, payload[key])
    db.commit()
    return user_public(current)


# --------------------------------------------------------------------------- #
# API-A4 · Unrestricted Resource Consumption (GET /api/v1/products?limit=)
# --------------------------------------------------------------------------- #
@router.get("/products")
def list_products_v1(
    limit: int = 20,
    current: User = Depends(get_api_user_v1),
    db: Session = Depends(get_db),
):
    products = db.execute(select(Product).order_by(Product.id)).scalars().all()
    if challenges.enabled("api.API-A4"):
        # LAB-VULN: API-A4 (intentional) — `limit` diterima tanpa batas/paginasi.
        items = [product_public(p) for p in products[:limit]]
        resp = {"limit_requested": limit, "capped": False, "count": len(items), "items": items}
        if limit > 1000:
            resp["flag"] = challenges.flag("api.API-A4")
        return resp
    # AMAN: batasi ukuran halaman.
    effective = max(1, min(limit, 100))
    items = [product_public(p) for p in products[:effective]]
    return {"limit_requested": limit, "limit_effective": effective, "capped": limit > 100, "count": len(items), "items": items}


# --------------------------------------------------------------------------- #
# API-A5 · Broken Function Level Authorization (POST /api/v1/admin/users/{id}/role)
# --------------------------------------------------------------------------- #
@router.post("/admin/users/{user_id}/role")
def admin_set_role_v1(
    user_id: int,
    payload: dict = Body(...),
    current: User = Depends(get_api_user_v1),
    db: Session = Depends(get_db),
):
    # LAB-VULN: API-A5 (intentional) — saat enabled, cek peran tidak dipasang di fungsi admin.
    if not challenges.enabled("api.API-A5") and current.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Butuh hak admin.")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan.")
    role = payload.get("role")
    if role in {"guest", "customer", "admin"}:
        target.role = role
        db.commit()
    data = {"id": target.id, "role": target.role}
    if challenges.enabled("api.API-A5") and current.role != "admin":
        data["flag"] = challenges.flag("api.API-A5")  # non-admin memanggil fungsi admin
    return data


# --------------------------------------------------------------------------- #
# API-A6 · Unrestricted Access to Business Flows (POST /api/v1/promo/claim)
# --------------------------------------------------------------------------- #
@router.post("/promo/claim")
def promo_claim_v1(current: User = Depends(get_api_user_v1)):
    if not challenges.enabled("api.API-A6") and promo.claim_count(current.id) >= 1:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Promo sudah diklaim (maks 1/user).")
    # LAB-VULN: API-A6 (intentional) — tanpa kuota per-user → alur bisnis bisa di-spam/borong.
    n = promo.add_claim(current.id)
    data = {"user_id": current.id, "claims": n}
    if challenges.enabled("api.API-A6") and n > 1:
        data["flag"] = challenges.flag("api.API-A6")
    return data


# --------------------------------------------------------------------------- #
# API-A7 · SSRF (POST /api/v1/fetch-url)
# --------------------------------------------------------------------------- #
@router.post("/fetch-url")
def fetch_url_v1(payload: dict = Body(...), current: User = Depends(get_api_user_v1)):
    url = str(payload.get("url", ""))
    if challenges.enabled("api.API-A7"):
        # LAB-VULN: API-A7 SSRF (intentional) — ambil URL user tanpa validasi tujuan.
        try:
            text, _ = fetch_url_unsafe(url)
        except Exception as exc:  # noqa: BLE001 — lab
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {"url": url, "response": text}
    # AMAN: validasi tujuan (anti-SSRF).
    try:
        content = fetch_bytes(url)
    except (UnsafeUrlError, Exception) as exc:  # noqa: BLE001 — lab
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"url": url, "bytes": len(content)}


# --------------------------------------------------------------------------- #
# API-A8 · Security Misconfiguration (GET /api/v1/server-info) + /docs terbuka
# --------------------------------------------------------------------------- #
@router.get("/server-info")
def server_info_v1():
    # LAB-VULN: API-A8 (intentional) — endpoint tak-terautentikasi membocorkan detail
    # server/konfigurasi; /docs & /openapi.json juga sengaja terbuka.
    if not challenges.enabled("api.API-A8"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {
        "python": platform.python_version(),
        "debug": settings.debug,
        "database_url": settings.database_url,
        "docs": "/docs (terbuka)",
        "openapi": "/openapi.json (terbuka)",
        "flag": challenges.flag("api.API-A8"),
    }


# --------------------------------------------------------------------------- #
# API-A10 · Unsafe Consumption of 3rd-party API (POST /api/v1/orders/{id}/pay)
# --------------------------------------------------------------------------- #
@router.post("/orders/{order_id}/pay")
def pay_order_v1(
    order_id: int,
    payload: dict = Body(...),
    current: User = Depends(get_api_user_v1),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None or order.user_id != current.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order tidak ditemukan.")
    gateway = payload.get("gateway_response", {}) or {}
    if challenges.enabled("api.API-A10"):
        # LAB-VULN: API-A10 (intentional) — percaya respons "gateway" dari klien mentah-mentah.
        if str(gateway.get("status")) == "paid":
            order.paid = True
            order.status = "paid"
            order.payment_ref = str(gateway.get("reference", "CLIENT-CLAIM"))
            db.commit()
            return {"order_id": order.id, "paid": True, "payment_ref": order.payment_ref, "flag": challenges.flag("api.API-A10")}
        return {"order_id": order.id, "paid": order.paid}
    # AMAN: abaikan klaim klien; server memproses & merekonsiliasi pembayaran sendiri.
    result = payments.charge(order.id, order.total)
    order.paid = result.success
    order.status = "paid" if result.success else order.status
    order.payment_ref = result.reference
    db.commit()
    return {"order_id": order.id, "paid": order.paid, "payment_ref": order.payment_ref}
