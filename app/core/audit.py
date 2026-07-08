"""Audit log aksi sensitif — target W-A09 (Security Logging & Monitoring Failures).

Info-level: yang diamati adalah ADA/TIDAKNYA jejak audit.
- AMAN (W-A09 disabled): aksi sensitif dicatat ke `records`.
- RENTAN (W-A09 enabled): pencatatan SENGAJA dilewati → tak ada jejak untuk deteksi.

State in-memory (cukup untuk lab & test). Di produksi gunakan log terstruktur + alerting.
"""

from __future__ import annotations

import logging

from app.core.challenges import challenges

logger = logging.getLogger("vulnshop.audit")

# Sink in-memory agar mudah diperiksa di test / demonstrasi.
records: list[dict] = []


def log_sensitive(event: str, **details) -> None:
    if challenges.enabled("web.W-A09"):
        # LAB-VULN: W-A09 (intentional) — aksi sensitif tidak dicatat (no audit trail).
        return
    entry = {"event": event, **details}
    records.append(entry)
    logger.info("AUDIT %s %s", event, details)


def clear() -> None:
    records.clear()
