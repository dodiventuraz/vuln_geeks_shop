"""Route autentikasi web (SSR): register, login, logout, lupa/reset password.

P1: SEMUA jalur AMAN — password di-hash pbkdf2 (salted), lookup parameterized (ORM),
token reset dari `secrets`. Titik kerentanan (Web-A03-a SQLi login, Web-A07-a brute force,
Web-A07-b token predictable) diberi penanda TODO untuk fase P2.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core import audit, ratelimit
from app.core.challenges import challenges
from app.core.db import get_db
from app.core.security import (
    create_access_token,
    find_user_for_login,
    get_current_user,
    get_user_by_email,
    hash_password,
    make_reset_token,
    verify_password,
)
from app.core.templating import templates
from app.models import User

router = APIRouter(tags=["web-auth"])


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("auth/register.html", {"request": request, "user": None})


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if get_user_by_email(db, email):
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "user": None, "error": "Email sudah terdaftar."},
            status_code=400,
        )
    new_user = User(
        email=email,
        name=name,
        password_hash=hash_password(password),  # AMAN: pbkdf2 salted
        role="customer",
    )
    db.add(new_user)
    db.commit()
    request.session["user_id"] = new_user.id
    return RedirectResponse("/", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, user=Depends(get_current_user)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("auth/login.html", {"request": request, "user": None})


def _establish_session(request: Request, user) -> None:
    """Set sesi login. Web-A07-b mengontrol regenerasi state sesi."""
    if not challenges.enabled("web.Web-A07-b"):
        # AMAN: regenerasi state sesi saat login (cegah session fixation).
        request.session.clear()
    # LAB-VULN: Web-A07-b (intentional) — saat enabled, state sesi pra-login TIDAK
    # diregenerasi, sehingga id sesi yang ditetapkan sebelum login tetap dipakai.
    request.session["user_id"] = user.id


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # Web-A07-a: cabang AMAN memberlakukan rate limit; enabled → tak dibatasi (brute force).
    if not challenges.enabled("web.Web-A07-a") and ratelimit.is_locked(email):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "user": None, "error": "Terlalu banyak percobaan. Coba lagi nanti."},
            status_code=429,
        )

    # Web-A03-a: find_user_for_login memilih jalur SQLi (rentan) / parameterized (aman).
    user = find_user_for_login(db, email)

    # LAB-VULN: Web-A03-a SQLi login (intentional) — bila query mengembalikan baris yang
    # email-nya TIDAK sama dengan input, berarti injeksi berhasil melewati password.
    if challenges.enabled("web.Web-A03-a") and user is not None and user.email != email:
        ratelimit.reset(email)
        _establish_session(request, user)
        request.session["lab_flag"] = challenges.flag("web.Web-A03-a")
        return RedirectResponse("/", status_code=303)

    if user is None or user.email != email or not verify_password(password, user.password_hash):
        ratelimit.record_failure(email)
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "user": None, "error": "Email atau password salah."},
            status_code=401,
        )

    prior_failures = ratelimit.failure_count(email)
    ratelimit.reset(email)
    _establish_session(request, user)
    # Web-A09: aksi sensitif (login berhasil) — dicatat hanya bila logging tidak "dimatikan".
    audit.log_sensitive("login_success", user_id=user.id, email=user.email)
    # LAB-VULN: Web-A07-a — login sukses setelah banyak kegagalan (brute force dibiarkan).
    if challenges.enabled("web.Web-A07-a") and prior_failures >= ratelimit.MAX_FAILURES:
        request.session["lab_flag"] = challenges.flag("web.Web-A07-a")
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@router.get("/forgot", response_class=HTMLResponse)
def forgot_form(request: Request):
    return templates.TemplateResponse("auth/forgot.html", {"request": request, "user": None})


@router.post("/forgot", response_class=HTMLResponse)
def forgot(request: Request, email: str = Form(...), db: Session = Depends(get_db)):
    user = get_user_by_email(db, email)
    reset_link = None
    if user:
        # Web-A07-b: make_reset_token memilih secrets (aman) / random ber-seed (predictable).
        user.reset_token = make_reset_token(user.id)
        user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        db.commit()
        # Lab: tampilkan link langsung (di produksi dikirim via email/mailhog).
        reset_link = f"/reset?token={user.reset_token}"
    return templates.TemplateResponse(
        "auth/forgot.html",
        {"request": request, "user": None, "sent": True, "reset_link": reset_link},
    )


@router.get("/reset", response_class=HTMLResponse)
def reset_form(request: Request, token: str = ""):
    return templates.TemplateResponse(
        "auth/reset.html", {"request": request, "user": None, "token": token}
    )


@router.post("/reset", response_class=HTMLResponse)
def reset(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    user = (
        db.query(User)
        .filter(User.reset_token == token)
        .filter(User.reset_token_expiry.isnot(None))
        .first()
    )
    expiry = user.reset_token_expiry if user else None
    # SQLite mengembalikan datetime naive; anggap UTC agar perbandingan konsisten lintas-DB.
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if user is None or expiry is None or expiry < now:
        return templates.TemplateResponse(
            "auth/reset.html",
            {"request": request, "user": None, "token": token, "error": "Token tidak valid/kedaluwarsa."},
            status_code=400,
        )
    user.password_hash = hash_password(password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.commit()
    if challenges.enabled("web.Web-A07-b"):
        # Bukti: reset berhasil lewat token yang bisa diprediksi (account takeover).
        request.session["lab_flag"] = challenges.flag("web.Web-A07-b")
        return RedirectResponse("/", status_code=303)
    return RedirectResponse("/login", status_code=303)
