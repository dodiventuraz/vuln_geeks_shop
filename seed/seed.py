"""Seed data DETERMINISTIK (REQ-S4).

Menyapu (drop) lalu membangun ulang skema, kemudian mengisi data awal yang sama
setiap kali dijalankan. Dipanggil oleh `make seed` dan `make reset`.

P1: data AMAN & fungsional. Beberapa akun/order sengaja disiapkan sebagai target
kerentanan fase berikutnya (mis. order milik user berbeda untuk IDOR Web-A01-a / BOLA API-A1).
"""

from __future__ import annotations

from decimal import Decimal

from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    Address,
    Category,
    Coupon,
    Order,
    OrderItem,
    Product,
    User,
)

# --- Akun deterministik (dipakai untuk login & dokumentasi) ---
SEED_USERS = [
    {"email": "admin@vulnshop.lab", "name": "Admin", "password": "Admin123!", "role": "admin", "is_verified": True, "balance": "0.00"},
    {"email": "alice@vulnshop.lab", "name": "Alice Customer", "password": "Password123", "role": "customer", "is_verified": True, "balance": "150.00"},
    {"email": "bob@vulnshop.lab", "name": "Bob Buyer", "password": "Password123", "role": "customer", "is_verified": True, "balance": "80.00"},
    {"email": "carol@vulnshop.lab", "name": "Carol Guest", "password": "Password123", "role": "customer", "is_verified": False, "balance": "0.00"},
]

SEED_CATEGORIES = [
    {"name": "Elektronik", "slug": "elektronik"},
    {"name": "Buku", "slug": "buku"},
    {"name": "Fashion", "slug": "fashion"},
    {"name": "Rumah Tangga", "slug": "rumah-tangga"},
]

# (name, slug, price, stock, category_slug, description)
SEED_PRODUCTS = [
    ("Mechanical Keyboard", "mechanical-keyboard", "45.00", 25, "elektronik", "Keyboard mekanik hot-swappable untuk geeks."),
    ("Noise-Cancelling Headphone", "nc-headphone", "120.00", 15, "elektronik", "Headphone ANC untuk fokus ngoding."),
    ("USB-C Hub 7-in-1", "usb-c-hub", "35.00", 40, "elektronik", "Hub USB-C serbaguna."),
    ("The Web Application Hacker's Handbook", "wahh", "50.00", 30, "buku", "Referensi klasik web pentest."),
    ("Clean Code", "clean-code", "28.00", 50, "buku", "Buku kualitas kode."),
    ("Hoodie 'Hack The Planet'", "hoodie-hack", "40.00", 20, "fashion", "Hoodie hangat bertema hacker."),
    ("Kaos Geek 'sudo make coffee'", "kaos-sudo", "18.00", 60, "fashion", "Kaos katun lucu."),
    ("Coffee Mug 'While(alive) code()'", "mug-code", "12.00", 100, "rumah-tangga", "Mug keramik 350ml."),
    ("Meja Standing Desk", "standing-desk", "220.00", 8, "rumah-tangga", "Meja berdiri elektrik."),
    ("Webcam 1080p", "webcam-1080p", "38.00", 22, "elektronik", "Webcam full-HD untuk meeting."),
]

SEED_COUPONS = [
    {"code": "WELCOME10", "percent_off": 10, "active": True, "max_uses": 1000, "used_count": 0},
    {"code": "SAVE20", "percent_off": 20, "active": True, "max_uses": 100, "used_count": 0},
    {"code": "EXPIRED", "percent_off": 50, "active": False, "max_uses": 0, "used_count": 0},
]


def run() -> None:
    # Sapu & bangun ulang skema agar state deterministik.
    import app.models  # noqa: F401 — pastikan model terdaftar di metadata

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Users
        users: dict[str, User] = {}
        for u in SEED_USERS:
            user = User(
                email=u["email"],
                name=u["name"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
                is_verified=u["is_verified"],
                balance=Decimal(u["balance"]),
            )
            db.add(user)
            users[u["email"]] = user

        # Categories
        cats: dict[str, Category] = {}
        for c in SEED_CATEGORIES:
            cat = Category(name=c["name"], slug=c["slug"])
            db.add(cat)
            cats[c["slug"]] = cat

        db.flush()  # dapatkan id user & kategori

        # Products
        products: dict[str, Product] = {}
        for name, slug, price, stock, cat_slug, desc in SEED_PRODUCTS:
            p = Product(
                name=name,
                slug=slug,
                price=Decimal(price),
                stock=stock,
                description=desc,
                category_id=cats[cat_slug].id,
            )
            db.add(p)
            products[slug] = p

        # Coupons
        for c in SEED_COUPONS:
            db.add(Coupon(**c))

        # Addresses
        db.add(Address(user_id=users["alice@vulnshop.lab"].id, line1="Jl. Merdeka 1", city="Jakarta", postal_code="10110", country="ID", phone="0811000001"))
        db.add(Address(user_id=users["bob@vulnshop.lab"].id, line1="Jl. Sudirman 45", city="Bandung", postal_code="40122", country="ID", phone="0811000002"))

        db.flush()

        # Sample orders (order milik user berbeda → target IDOR/BOLA nanti)
        def make_order(owner_email: str, items: list[tuple[str, int]], coupon: str | None = None) -> None:
            owner = users[owner_email]
            order = Order(user_id=owner.id, status="paid", paid=True, payment_ref="PAY-SEED")
            subtotal = Decimal("0.00")
            for slug, qty in items:
                prod = products[slug]
                subtotal += Decimal(prod.price) * qty
                order.items.append(
                    OrderItem(product_id=prod.id, product_name=prod.name, unit_price=Decimal(prod.price), quantity=qty)
                )
            discount = Decimal("0.00")
            if coupon:
                order.coupon_code = coupon
                discount = (subtotal * Decimal(10) / Decimal(100)).quantize(Decimal("0.01"))
            order.subtotal = subtotal
            order.discount = discount
            order.total = subtotal - discount
            db.add(order)

        make_order("alice@vulnshop.lab", [("mechanical-keyboard", 1), ("mug-code", 2)], coupon="WELCOME10")
        make_order("bob@vulnshop.lab", [("nc-headphone", 1)])

        db.commit()
        print(
            f"[seed] OK — {len(SEED_USERS)} user, {len(SEED_CATEGORIES)} kategori, "
            f"{len(SEED_PRODUCTS)} produk, {len(SEED_COUPONS)} kupon, 2 order contoh."
        )
    finally:
        db.close()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
