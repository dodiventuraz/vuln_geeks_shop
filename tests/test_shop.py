"""Test fungsional belanja: tambah ke cart, checkout, ownership order (P1 — AMAN)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_add_to_cart_and_checkout(registered_client: TestClient, sample_product):
    client = registered_client

    add = client.post(
        "/cart/add",
        data={"product_id": sample_product.id, "quantity": 2},
        follow_redirects=False,
    )
    assert add.status_code == 303

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert "Test Product" in cart.text

    checkout = client.post("/checkout", data={"coupon_code": ""}, follow_redirects=False)
    assert checkout.status_code == 303
    assert "/orders/" in checkout.headers["location"]

    # Order muncul di riwayat & bertanda LUNAS (payment mock sukses).
    orders = client.get("/orders")
    assert orders.status_code == 200
    detail = client.get(checkout.headers["location"])
    assert detail.status_code == 200
    assert "LUNAS" in detail.text


def test_order_ownership_enforced(client: TestClient, sample_product):
    # User A buat order.
    client.post("/register", data={"email": "a@vulnshop.lab", "name": "A", "password": "Password123"}, follow_redirects=False)
    client.post("/cart/add", data={"product_id": sample_product.id, "quantity": 1}, follow_redirects=False)
    co = client.post("/checkout", data={"coupon_code": ""}, follow_redirects=False)
    order_path = co.headers["location"]  # mis. /orders/1
    client.get("/logout")

    # User B tidak boleh melihat order milik A (AMAN: 404).
    client.post("/register", data={"email": "b@vulnshop.lab", "name": "B", "password": "Password123"}, follow_redirects=False)
    resp = client.get(order_path)
    assert resp.status_code == 404


def test_search_filters_products(client: TestClient, sample_product):
    resp = client.get("/", params={"q": "Test Product"})
    assert resp.status_code == 200
    assert "Test Product" in resp.text

    resp_none = client.get("/", params={"q": "TidakAda__XYZ"})
    assert resp_none.status_code == 200
    assert "Test Product" not in resp_none.text


def test_coupon_applies_discount(registered_client: TestClient, sample_product, db):
    from app.models import Coupon

    db.add(Coupon(code="HALF", percent_off=50, active=True, max_uses=10, used_count=0))
    db.commit()

    client = registered_client
    client.post("/cart/add", data={"product_id": sample_product.id, "quantity": 1}, follow_redirects=False)
    co = client.post("/checkout", data={"coupon_code": "HALF"}, follow_redirects=False)
    detail = client.get(co.headers["location"])
    # Harga 10.00, diskon 50% → total 5.00
    assert "5.00" in detail.text


def test_admin_area_forbidden_for_customer(registered_client: TestClient):
    resp = registered_client.get("/admin", follow_redirects=False)
    assert resp.status_code == 403
