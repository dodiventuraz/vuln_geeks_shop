"""Smoke test P0: /health hidup + header lab terpasang.

Test ini tidak butuh Postgres aktif: /health menangkap error koneksi DB dan tetap
mengembalikan 200 (dengan status 'degraded' + detail error).
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200

    body = resp.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["app"] == "Vuln Geeks Shop"
    assert "database" in body
    assert "ok" in body["database"]


def test_lab_warning_header_present(client: TestClient) -> None:
    """REQ-S2: setiap respons wajib membawa header X-Lab-Warning."""
    resp = client.get("/health")
    assert resp.headers.get("X-Lab-Warning") == "INTENTIONALLY VULNERABLE - LAB USE ONLY"
