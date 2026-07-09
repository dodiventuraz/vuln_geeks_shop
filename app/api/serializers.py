"""Serializer dict untuk respons API.

`user_full` sengaja membocorkan field sensitif (password_hash/PII) — dipakai hanya
di jalur rentan API-A3-b. `user_public` adalah bentuk aman (field terbatas).
"""

from __future__ import annotations

from app.models import Order, Product, User


def product_public(p: Product) -> dict:
    return {"id": p.id, "name": p.name, "slug": p.slug, "price": str(p.price), "stock": p.stock}


def user_public(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role}


def user_full(u: User) -> dict:
    # LAB-VULN: API-A3-b — schema penuh membocorkan password_hash/PII/saldo.
    return {
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "balance": str(u.balance),
        "is_verified": u.is_verified,
        "password_hash": u.password_hash,
        "card_number": u.card_number,
        "reset_token": u.reset_token,
        "avatar_path": u.avatar_path,
    }


def order_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "user_id": o.user_id,
        "status": o.status,
        "paid": o.paid,
        "total": str(o.total),
        "coupon_code": o.coupon_code,
        "items": [
            {"product_name": it.product_name, "unit_price": str(it.unit_price), "quantity": it.quantity}
            for it in o.items
        ],
    }
