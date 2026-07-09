"""Route profil user (SSR): lihat/ubah profil, kelola alamat, upload avatar, billing.

P1 AMAN: user hanya bisa mengubah field profilnya sendiri (name/email).
Kerentanan (toggle):
- Web-A02-a: bila enabled, panel profil membocorkan `password_hash` (md5 tak ber-salt).
- Web-A02-b: bila enabled, kartu pembayaran disimpan & ditampilkan plaintext (PII).
TODO[P3] API-A3-a: mass assignment via API `PATCH /api/user` menyusul di fase P3.
"""

from __future__ import annotations

import os

import yaml
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.challenges import challenges
from app.core.db import get_db
from app.core.security import require_login
from app.core.templating import templates
from app.web.uploads import save_upload
from app.models import Address

router = APIRouter(tags=["web-profile"])

# "Rahasia" yang bisa dibaca lewat insecure deserialization (Web-A08).
os.environ.setdefault("LAB_DESER_FLAG", challenges.flag("web.Web-A08") or "")


def _profile_ctx(request: Request, user, **extra) -> dict:
    ctx = {"request": request, "user": user}
    # Web-A02-a: bocorkan hash md5 (crackable) di panel profil bila enabled.
    ctx["weak_hash"] = (
        user.password_hash
        if challenges.enabled("web.Web-A02-a") and (user.password_hash or "").startswith("md5$")
        else None
    )
    # Web-A02-b: tandai bila kartu tersimpan plaintext (bukan hasil mask).
    ctx["pii_plaintext"] = bool(
        challenges.enabled("web.Web-A02-b")
        and user.card_number
        and not user.card_number.startswith("****")
    )
    ctx.update(extra)
    return ctx


@router.get("/profile", response_class=HTMLResponse)
def profile_view(request: Request, user=Depends(require_login)):
    return templates.TemplateResponse("profile.html", _profile_ctx(request, user))


@router.post("/profile")
def profile_update(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    # AMAN: allowlist field. Tidak menyentuh role/balance/is_verified.
    user.name = name
    user.email = email
    db.commit()
    return templates.TemplateResponse("profile.html", _profile_ctx(request, user, saved=True))


@router.post("/profile/avatar")
def upload_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    error = None
    try:
        user.avatar_path = save_upload(avatar, prefix=f"avatar{user.id}")
        db.commit()
    except ValueError as exc:
        error = str(exc)
    return templates.TemplateResponse(
        "profile.html", _profile_ctx(request, user, saved=error is None, error=error)
    )


@router.post("/profile/billing")
def save_billing(
    card_number: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    if challenges.enabled("web.Web-A02-b"):
        # LAB-VULN: Web-A02-b (intentional) — simpan nomor kartu (PAN) plaintext di DB.
        user.card_number = card_number
    else:
        # AMAN: tokenisasi — jangan simpan PAN penuh, cukup mask + 4 digit terakhir.
        digits = "".join(ch for ch in card_number if ch.isdigit())
        user.card_number = f"**** **** **** {digits[-4:]}" if len(digits) >= 4 else None
    db.commit()
    return RedirectResponse("/profile", status_code=303)


@router.get("/preferences", response_class=HTMLResponse)
def preferences_form(request: Request, user=Depends(require_login)):
    return templates.TemplateResponse("preferences.html", {"request": request, "user": user})


@router.post("/preferences/import", response_class=HTMLResponse)
def preferences_import(
    request: Request,
    data: str = Form(...),
    user=Depends(require_login),
):
    """Restore preferensi dari blob YAML. Target Web-A08 (insecure deserialization)."""
    result = None
    error = None
    try:
        if challenges.enabled("web.Web-A08"):
            # LAB-VULN: Web-A08 (intentional) — loader penuh mengeksekusi tag Python
            # (mis. !!python/object/apply:os.system / os.getenv) → RCE primitive.
            result = yaml.load(data, Loader=yaml.UnsafeLoader)  # noqa: S506
        else:
            # AMAN: hanya tipe dasar; tag Python ditolak.
            result = yaml.safe_load(data)
    except Exception as exc:  # noqa: BLE001 — lab: tampilkan error parsing
        error = str(exc)
    return templates.TemplateResponse(
        "preferences.html",
        {"request": request, "user": user, "data": data, "result": repr(result), "error": error},
    )


@router.post("/profile/address")
def add_address(
    line1: str = Form(...),
    city: str = Form(...),
    postal_code: str = Form(...),
    country: str = Form("ID"),
    phone: str = Form(""),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    db.add(
        Address(
            user_id=user.id,
            line1=line1,
            city=city,
            postal_code=postal_code,
            country=country,
            phone=phone or None,
        )
    )
    db.commit()
    return RedirectResponse("/profile", status_code=303)
