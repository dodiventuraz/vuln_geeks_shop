"""Route keranjang & checkout (SSR).

P1 AMAN: kuantitas dipaksa positif (W-A04a nanti melonggarkan), checkout berurutan
dalam satu transaksi (W-A04b race condition menyusul di P2).
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import services
from app.core.challenges import challenges
from app.core.db import get_db
from app.core.security import require_login
from app.core.templating import templates
from app.models import Address, CartItem

router = APIRouter(tags=["web-cart"])


@router.get("/cart", response_class=HTMLResponse)
def cart_view(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    cart = services.get_or_create_cart(db, user)
    totals = services.cart_totals(cart)
    return templates.TemplateResponse(
        "cart.html", {"request": request, "user": user, "cart": cart, "totals": totals}
    )


@router.post("/cart/add")
def cart_add(
    product_id: int = Form(...),
    quantity: int = Form(1),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    try:
        services.add_to_cart(db, user, product_id, quantity)
    except services.CheckoutError:
        pass
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/update")
def cart_update(
    item_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    item = db.get(CartItem, item_id)
    # AMAN: pastikan item milik cart user sendiri (cegah IDOR pada cart item).
    if item and item.cart.user_id == user.id:
        services.set_cart_quantity(db, item, quantity)
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/remove")
def cart_remove(
    item_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    item = db.get(CartItem, item_id)
    if item and item.cart.user_id == user.id:
        db.delete(item)
        db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.get("/checkout", response_class=HTMLResponse)
def checkout_form(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    cart = services.get_or_create_cart(db, user)
    totals = services.cart_totals(cart)
    addresses = db.execute(select(Address).where(Address.user_id == user.id)).scalars().all()
    return templates.TemplateResponse(
        "checkout.html",
        {"request": request, "user": user, "cart": cart, "totals": totals, "addresses": addresses},
    )


@router.post("/checkout")
def checkout_submit(
    request: Request,
    address_id: int | None = Form(None),
    coupon_code: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    # AMAN: verifikasi address milik user bila diberikan.
    if address_id is not None:
        addr = db.get(Address, address_id)
        if addr is None or addr.user_id != user.id:
            address_id = None
    try:
        order = services.checkout(db, user, address_id=address_id, coupon_code=coupon_code or None)
    except services.CheckoutError as exc:
        cart = services.get_or_create_cart(db, user)
        totals = services.cart_totals(cart)
        addresses = db.execute(select(Address).where(Address.user_id == user.id)).scalars().all()
        return templates.TemplateResponse(
            "checkout.html",
            {
                "request": request,
                "user": user,
                "cart": cart,
                "totals": totals,
                "addresses": addresses,
                "error": str(exc),
            },
            status_code=400,
        )
    # W-A04a: total negatif (dari qty negatif) → bukti manipulasi business logic.
    if challenges.enabled("web.W-A04a") and order.total < Decimal("0"):
        request.session["lab_flag"] = challenges.flag("web.W-A04a")
    return RedirectResponse(f"/orders/{order.id}", status_code=303)


@router.post("/coupon/redeem")
def coupon_redeem(
    code: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    """Redeem kupon (satu-per-request). Target W-A04b (race condition/TOCTOU)."""
    success = services.redeem_coupon(db, code)
    body: dict = {"success": success}
    if success and challenges.enabled("web.W-A04b"):
        # Bukti dapat diperbanyak melewati batas via race (lihat exploit-test).
        body["flag"] = challenges.flag("web.W-A04b")
    return JSONResponse(body)
