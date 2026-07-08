"""Test scoreboard: submit flag benar/salah & progres."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_scoreboard_loads(client: TestClient):
    resp = client.get("/scoreboard")
    assert resp.status_code == 200
    assert "Scoreboard" in resp.text


def test_submit_correct_flag_marks_solved(client: TestClient):
    resp = client.post("/submit-flag", data={"flag": "FLAG{idor_orders}"}, follow_redirects=False)
    assert resp.status_code == 200
    assert "web.W-A01a" in resp.text
    assert "solved" in resp.text.lower()
    # Progres tersimpan di sesi berikutnya.
    again = client.get("/scoreboard")
    assert "✔ solved" in again.text


def test_submit_wrong_flag_rejected(client: TestClient):
    resp = client.post("/submit-flag", data={"flag": "FLAG{bukan_flag}"}, follow_redirects=False)
    assert resp.status_code == 200
    assert "tidak dikenali" in resp.text.lower()


def test_api_flag_accepted(client: TestClient):
    resp = client.post("/submit-flag", data={"flag": "FLAG{bola_orders}"}, follow_redirects=False)
    assert "api.A-1" in resp.text
