"""Test fungsional autentikasi (P1 — jalur AMAN)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_creates_session_and_logs_in(client: TestClient):
    resp = client.post(
        "/register",
        data={"email": "new@vulnshop.lab", "name": "New User", "password": "Password123"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    # Setelah register, profil (butuh login) bisa diakses.
    profile = client.get("/profile")
    assert profile.status_code == 200
    assert "New User" in profile.text


def test_login_wrong_password_rejected(client: TestClient):
    client.post(
        "/register",
        data={"email": "u1@vulnshop.lab", "name": "U1", "password": "Password123"},
        follow_redirects=False,
    )
    client.get("/logout")
    bad = client.post(
        "/login",
        data={"email": "u1@vulnshop.lab", "password": "salah"},
        follow_redirects=False,
    )
    assert bad.status_code == 401


def test_login_correct_password_ok(client: TestClient):
    client.post(
        "/register",
        data={"email": "u2@vulnshop.lab", "name": "U2", "password": "Password123"},
        follow_redirects=False,
    )
    client.get("/logout")
    ok = client.post(
        "/login",
        data={"email": "u2@vulnshop.lab", "password": "Password123"},
        follow_redirects=False,
    )
    assert ok.status_code == 303


def test_protected_page_requires_login(client: TestClient):
    resp = client.get("/orders")
    assert resp.status_code == 401


def test_api_jwt_token_issued(client: TestClient):
    client.post(
        "/register",
        data={"email": "api@vulnshop.lab", "name": "Api", "password": "Password123"},
        follow_redirects=False,
    )
    resp = client.post(
        "/api/v1/auth/token",
        json={"email": "api@vulnshop.lab", "password": "Password123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
