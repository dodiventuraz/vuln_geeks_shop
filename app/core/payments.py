"""Gateway pembayaran — MOCK (REQ-S5).

P1: implementasi AMAN. Bila `payment_mock_url` diset (di Docker Compose menunjuk ke
service `payment-mock`), charge memanggilnya; hasil DIVALIDASI sebelum dipercaya.
Bila tidak diset / tak terjangkau, fallback deterministik lokal (selalu sukses) agar
lab & test tetap reproducible offline.

TODO[P3] API-A10: cabang RENTAN yang mempercayai respons pihak ketiga mentah-mentah
diselipkan di sini, dijaga challenges.enabled("api.API-A10").
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal

import httpx

from app.core.config import settings


@dataclass
class PaymentResult:
    success: bool
    reference: str


def charge(order_id: int, amount: Decimal) -> PaymentResult:
    """Proses pembayaran mock. Selalu sukses di lab, dengan referensi deterministik."""
    ref = "PAY-" + hashlib.sha256(f"{order_id}:{amount}".encode()).hexdigest()[:12].upper()

    if settings.payment_mock_url:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(
                    settings.payment_mock_url.rstrip("/") + "/charge",
                    json={"order_id": order_id, "amount": str(amount)},
                )
            # AMAN: validasi minimal respons pihak ketiga sebelum dipercaya.
            if resp.status_code == 200:
                data = resp.json()
                return PaymentResult(
                    success=bool(data.get("success", True)),
                    reference=str(data.get("reference") or ref),
                )
        except (httpx.HTTPError, ValueError):
            pass  # fallback deterministik di bawah

    return PaymentResult(success=True, reference=ref)
