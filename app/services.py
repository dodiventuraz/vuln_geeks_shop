"""Logika bisnis e-commerce.

Kerentanan yang di-toggle di sini (P2):
- Web-A04-a (qty negatif): `add_to_cart` melonggarkan validasi kuantitas saat enabled.
- Web-A04-b (race kupon TOCTOU): `redeem_coupon` memilih jalur CHECK+USE (rentan) vs atomik (aman).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import payments
from app.core.challenges import challenges
from app.models import Cart, CartItem, Coupon, Order, OrderItem, Product


class CheckoutError(Exception):
    pass


def get_or_create_cart(db: Session, user) -> Cart:
    cart = db.execute(select(Cart).where(Cart.user_id == user.id)).scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def add_to_cart(db: Session, user, product_id: int, quantity: int = 1) -> CartItem:
    if challenges.enabled("web.Web-A04-a"):
        # LAB-VULN: Web-A04-a business logic (intentional) — kuantitas TIDAK divalidasi
        # (boleh negatif) → total bisa jadi negatif.
        quantity = int(quantity)
    else:
        # AMAN: kuantitas dipaksa >= 1.
        quantity = max(1, int(quantity))
    product = db.get(Product, product_id)
    if product is None:
        raise CheckoutError("Produk tidak ditemukan.")

    cart = get_or_create_cart(db, user)
    item = db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.product_id == product_id)
    ).scalar_one_or_none()
    if item is None:
        item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
        db.add(item)
    else:
        item.quantity += quantity
    db.commit()
    db.refresh(item)
    return item


def set_cart_quantity(db: Session, item: CartItem, quantity: int) -> None:
    if quantity <= 0:
        db.delete(item)
    else:
        item.quantity = quantity
    db.commit()


# --------------------------------------------------------------------------- #
# Redeem kupon — target Web-A04-b (race condition / TOCTOU).
# Fase "check" dan "consume" sengaja dipisah pada jalur rentan (celah TOCTOU).
# --------------------------------------------------------------------------- #
def coupon_check(db: Session, code: str) -> Coupon | None:
    """CHECK: kembalikan coupon bila masih boleh dipakai, atau None."""
    coupon = db.execute(
        select(Coupon).where(Coupon.code == code, Coupon.active.is_(True))
    ).scalar_one_or_none()
    if coupon and coupon.used_count < coupon.max_uses:
        return coupon
    return None


def coupon_consume_unsafe(db: Session, coupon: Coupon) -> None:
    """USE (rentan): increment tanpa re-check/atomicity — ada gap dari CHECK."""
    coupon.used_count += 1
    db.commit()


def coupon_consume_atomic(db: Session, code: str) -> bool:
    """USE (aman): dekremen kondisional atomik — cek & pakai dalam satu statement."""
    result = db.execute(
        update(Coupon)
        .where(Coupon.code == code, Coupon.used_count < Coupon.max_uses)
        .values(used_count=Coupon.used_count + 1)
    )
    db.commit()
    return result.rowcount == 1


def redeem_coupon(db: Session, code: str) -> bool:
    """Redeem satu kali. Web-A04-b memilih jalur TOCTOU (rentan) / atomik (aman)."""
    if challenges.enabled("web.Web-A04-b"):
        # LAB-VULN: Web-A04-b TOCTOU (intentional) — CHECK lalu USE tanpa lock/atomicity.
        coupon = coupon_check(db, code)
        if coupon is None:
            return False
        coupon_consume_unsafe(db, coupon)
        return True
    return coupon_consume_atomic(db, code)


def cart_totals(cart: Cart) -> dict:
    subtotal = Decimal("0.00")
    for it in cart.items:
        subtotal += Decimal(it.product.price) * it.quantity
    return {"subtotal": subtotal, "item_count": sum(it.quantity for it in cart.items)}


def _resolve_coupon(db: Session, code: str | None) -> Coupon | None:
    if not code:
        return None
    coupon = db.execute(select(Coupon).where(Coupon.code == code)).scalar_one_or_none()
    if coupon and coupon.active and coupon.used_count < coupon.max_uses:
        return coupon
    return None


def checkout(db: Session, user, *, address_id: int | None, coupon_code: str | None) -> Order:
    """Buat order dari isi cart, terapkan kupon, bayar (mock), kurangi stok.

    P1 AMAN: pengecekan & pemakaian stok/kupon dilakukan berurutan dalam satu
    transaksi. TODO[P2] Web-A04-b: versi TOCTOU tanpa lock diselipkan di fase P2.
    """
    cart = get_or_create_cart(db, user)
    if not cart.items:
        raise CheckoutError("Keranjang kosong.")

    subtotal = Decimal("0.00")
    order = Order(user_id=user.id, address_id=address_id, status="pending")
    for it in cart.items:
        product = it.product
        if product.stock < it.quantity:
            raise CheckoutError(f"Stok '{product.name}' tidak cukup.")
        unit_price = Decimal(product.price)
        subtotal += unit_price * it.quantity
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                unit_price=unit_price,
                quantity=it.quantity,
            )
        )

    coupon = _resolve_coupon(db, coupon_code)
    discount = Decimal("0.00")
    if coupon:
        discount = (subtotal * Decimal(coupon.percent_off) / Decimal(100)).quantize(Decimal("0.01"))
        order.coupon_code = coupon.code

    order.subtotal = subtotal
    order.discount = discount
    order.total = subtotal - discount

    # Kurangi stok & pakai kupon (jalur aman, dalam transaksi yang sama).
    for it in cart.items:
        it.product.stock -= it.quantity
    if coupon:
        coupon.used_count += 1

    db.add(order)
    db.flush()  # dapatkan order.id sebelum charge

    result = payments.charge(order.id, order.total)
    if result.success:
        order.paid = True
        order.status = "paid"
        order.payment_ref = result.reference

    # Kosongkan cart
    for it in list(cart.items):
        db.delete(it)

    db.commit()
    db.refresh(order)
    return order
