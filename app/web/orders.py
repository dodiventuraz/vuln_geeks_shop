"""Route riwayat/detail order & invoice (SSR).

P1 AMAN: setiap akses order/invoice DIVERIFIKASI kepemilikannya terhadap
`current_user`. TODO[P2] Web-A01-a: cabang IDOR (ambil by id tanpa cek pemilik)
diselipkan di sini, dijaga challenges.enabled("web.Web-A01-a").
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.challenges import challenges
from app.core.db import get_db
from app.core.security import require_login
from app.core.templating import templates
from app.models import Order

router = APIRouter(tags=["web-orders"])


def _get_owned_order(db: Session, order_id: int, user) -> Order | None:
    """AMAN: filter by id DAN pemilik. Kembalikan None bila bukan milik user."""
    return db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user.id)
    ).scalar_one_or_none()


def _resolve_order(db: Session, order_id: int, user) -> tuple[Order | None, str | None]:
    """Kembalikan (order, flag). Web-A01-a mengontrol apakah kepemilikan dicek."""
    if challenges.enabled("web.Web-A01-a"):
        # LAB-VULN: Web-A01-a IDOR (intentional) — ambil object by id TANPA cek current_user.
        order = db.get(Order, order_id)
        flag = None
        if order is not None and order.user_id != user.id:
            flag = challenges.flag("web.Web-A01-a")  # bukti akses order milik user lain
        return order, flag
    # AMAN: hanya order milik user sendiri.
    return _get_owned_order(db, order_id, user), None


@router.get("/orders", response_class=HTMLResponse)
def order_list(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    orders = db.execute(
        select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
    ).scalars().all()
    return templates.TemplateResponse(
        "orders.html", {"request": request, "user": user, "orders": orders}
    )


@router.get("/orders/{order_id}", response_class=HTMLResponse)
def order_detail(order_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    order, flag = _resolve_order(db, order_id, user)
    # Flag hasil eksploitasi lain yang di-stash di session (mis. Web-A04-a total negatif).
    flag = flag or request.session.pop("lab_flag", None)
    if order is None:
        return templates.TemplateResponse(
            "message.html",
            {"request": request, "user": user, "title": "404", "message": "Order tidak ditemukan."},
            status_code=404,
        )
    return templates.TemplateResponse(
        "order_detail.html", {"request": request, "user": user, "order": order, "flag": flag}
    )


@router.get("/invoice/{order_id}", response_class=HTMLResponse)
def invoice(order_id: int, request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    order, flag = _resolve_order(db, order_id, user)
    if order is None:
        return templates.TemplateResponse(
            "message.html",
            {"request": request, "user": user, "title": "404", "message": "Invoice tidak ditemukan."},
            status_code=404,
        )
    return templates.TemplateResponse(
        "invoice.html", {"request": request, "user": user, "order": order, "flag": flag}
    )
