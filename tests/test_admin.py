"""Test fungsional admin + validasi anti-SSRF import URL (P1 — AMAN)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.net import UnsafeUrlError, validate_public_url


@pytest.fixture()
def admin_client(client: TestClient, db) -> TestClient:
    from app.core.security import hash_password
    from app.models import User

    db.add(User(email="root@vulnshop.lab", name="Root", password_hash=hash_password("Admin123!"), role="admin"))
    db.commit()
    client.post("/login", data={"email": "root@vulnshop.lab", "password": "Admin123!"}, follow_redirects=False)
    return client


def test_admin_can_create_product(admin_client: TestClient):
    resp = admin_client.post(
        "/admin/products/create",
        data={"name": "Admin Made", "price": "9.99", "stock": "3", "description": "x"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    listing = admin_client.get("/admin/products")
    assert "Admin Made" in listing.text


def test_admin_dashboard_accessible(admin_client: TestClient):
    resp = admin_client.get("/admin")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1/", "http://localhost/admin", "http://169.254.169.254/latest/meta-data/", "file:///etc/passwd"],
)
def test_import_url_rejects_internal_targets(url: str):
    """P1 AMAN: tujuan internal/non-publik & skema non-http DITOLAK (anti-SSRF)."""
    with pytest.raises(UnsafeUrlError):
        validate_public_url(url)
