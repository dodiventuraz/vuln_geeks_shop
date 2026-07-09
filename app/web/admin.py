"""Admin panel (SSR): CRUD produk, kelola user & order, upload gambar,
import produk dari URL.

Kerentanan (toggle via challenges.yaml):
- Web-A01-b: forced browsing ke area admin — role check tak dipasang pada halaman view.
- Web-A01-c: missing function-level check pada mutasi produk (update/hapus).
- Web-A10 (fase berikutnya): SSRF via import URL — masih AMAN (validasi tujuan) di batch ini.
"""

from __future__ import annotations

import os
import re
import secrets
import subprocess
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.challenges import challenges
from app.core.db import get_db
from app.core.net import UnsafeUrlError, fetch_bytes, fetch_url_unsafe
from app.core.security import require_admin, require_login
from app.core.templating import templates
from app.web.uploads import save_bytes, save_upload
from app.models import Category, Order, Product, User

router = APIRouter(prefix="/admin", tags=["web-admin"])

# "Rahasia" yang bisa dibaca lewat command injection (Web-A03-d): echo $LAB_CMD_FLAG.
os.environ.setdefault("LAB_CMD_FLAG", challenges.flag("web.Web-A03-d") or "")

_HOST_RE = re.compile(r"^[A-Za-z0-9.\-]+$")


def _ping_count_flag() -> str:
    return "-n" if os.name == "nt" else "-c"


# --------------------------------------------------------------------------- #
# Access guards (branching)
# --------------------------------------------------------------------------- #
def admin_view_access(user=Depends(require_login)):
    """Akses halaman view admin. Web-A01-b mengontrol apakah role dicek."""
    if challenges.enabled("web.Web-A01-b"):
        # LAB-VULN: Web-A01-b (intentional) — dependency role admin "tak dipasang":
        # user biasa yang login bisa forced-browse ke area admin.
        return user
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Butuh hak admin.")
    return user


def product_mutate_access(user=Depends(require_login)):
    """Akses mutasi produk (update/hapus). Web-A01-c mengontrol apakah role dicek."""
    if challenges.enabled("web.Web-A01-c"):
        # LAB-VULN: Web-A01-c (intentional) — mutasi produk tak memverifikasi peran pemanggil.
        return user
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Butuh hak admin.")
    return user


def _slugify(name: str) -> str:
    return "-".join("".join(c.lower() if c.isalnum() else " " for c in name).split())


def _products_page(request, db, user, *, flag=None, error=None, ssrf_preview=None, status_code=200):
    items = db.execute(select(Product).order_by(Product.id)).scalars().all()
    categories = db.execute(select(Category).order_by(Category.name)).scalars().all()
    return templates.TemplateResponse(
        "admin/products.html",
        {
            "request": request,
            "user": user,
            "products": items,
            "categories": categories,
            "flag": flag,
            "error": error,
            "ssrf_preview": ssrf_preview,
        },
        status_code=status_code,
    )


# --------------------------------------------------------------------------- #
# Dashboard & daftar (view — dijaga admin_view_access, target Web-A01-b)
# --------------------------------------------------------------------------- #
@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), viewer=Depends(admin_view_access)):
    flag = None
    if viewer.role != "admin" and challenges.enabled("web.Web-A01-b"):
        flag = challenges.flag("web.Web-A01-b")  # bukti: non-admin membuka dashboard admin
    stats = {
        "products": db.scalar(select(func.count()).select_from(Product)),
        "users": db.scalar(select(func.count()).select_from(User)),
        "orders": db.scalar(select(func.count()).select_from(Order)),
    }
    return templates.TemplateResponse(
        "admin/dashboard.html", {"request": request, "user": viewer, "stats": stats, "flag": flag}
    )


@router.get("/products", response_class=HTMLResponse)
def products(request: Request, db: Session = Depends(get_db), viewer=Depends(admin_view_access)):
    return _products_page(request, db, viewer)


@router.get("/users", response_class=HTMLResponse)
def users(request: Request, db: Session = Depends(get_db), viewer=Depends(admin_view_access)):
    items = db.execute(select(User).order_by(User.id)).scalars().all()
    return templates.TemplateResponse(
        "admin/users.html", {"request": request, "user": viewer, "users": items}
    )


@router.get("/orders", response_class=HTMLResponse)
def orders(request: Request, db: Session = Depends(get_db), viewer=Depends(admin_view_access)):
    items = db.execute(select(Order).order_by(Order.created_at.desc())).scalars().all()
    return templates.TemplateResponse(
        "admin/orders.html", {"request": request, "user": viewer, "orders": items}
    )


# --------------------------------------------------------------------------- #
# Mutasi produk (update/hapus — target Web-A01-c)
# --------------------------------------------------------------------------- #
@router.post("/products/create")
def product_create(
    name: str = Form(...),
    price: str = Form("0"),
    stock: int = Form(0),
    description: str = Form(""),
    category_id: int | None = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),  # AMAN (strict): create bukan target Web-A01-c.
):
    try:
        price_dec = Decimal(price)
    except InvalidOperation:
        price_dec = Decimal("0.00")
    product = Product(
        name=name,
        slug=_slugify(name) or f"produk-{secrets.token_hex(4)}",
        price=price_dec,
        stock=int(stock),
        description=description,
        category_id=category_id or None,
    )
    db.add(product)
    db.commit()
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/products/{product_id}/update")
def product_update(
    product_id: int,
    request: Request,
    name: str = Form(...),
    price: str = Form("0"),
    stock: int = Form(0),
    description: str = Form(""),
    db: Session = Depends(get_db),
    actor=Depends(product_mutate_access),
):
    product = db.get(Product, product_id)
    if product:
        product.name = name
        try:
            product.price = Decimal(price)
        except InvalidOperation:
            pass
        product.stock = int(stock)
        product.description = description
        db.commit()
    if actor.role != "admin" and challenges.enabled("web.Web-A01-c"):
        return _products_page(request, db, actor, flag=challenges.flag("web.Web-A01-c"))
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/products/{product_id}/delete")
def product_delete(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor=Depends(product_mutate_access),
):
    product = db.get(Product, product_id)
    if product:
        db.delete(product)
        db.commit()
    if actor.role != "admin" and challenges.enabled("web.Web-A01-c"):
        return _products_page(request, db, actor, flag=challenges.flag("web.Web-A01-c"))
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/products/{product_id}/image")
def product_image(
    product_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    product = db.get(Product, product_id)
    if product:
        try:
            product.image_path = save_upload(image, prefix=f"product{product_id}")
            db.commit()
        except ValueError:
            pass
    return RedirectResponse("/admin/products", status_code=303)


@router.post("/products/{product_id}/import-image")
def product_import_image(
    product_id: int,
    request: Request,
    image_url: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    product = db.get(Product, product_id)
    error = None
    ssrf_preview = None
    if product:
        try:
            if challenges.enabled("web.Web-A10"):
                # LAB-VULN: Web-A10 SSRF (intentional) — ambil URL user tanpa validasi tujuan.
                preview, data = fetch_url_unsafe(image_url)
                ssrf_preview = preview  # respons internal bocor ke penyerang
                try:
                    product.image_path = save_bytes(data, prefix=f"product{product_id}")
                except ValueError:
                    pass  # bukan gambar (mis. respons metadata) — abaikan simpan
                db.commit()
            else:
                # AMAN: validasi tujuan (anti-SSRF).
                data = fetch_bytes(image_url)
                product.image_path = save_bytes(data, prefix=f"product{product_id}")
                db.commit()
        except (UnsafeUrlError, Exception) as exc:  # noqa: BLE001 — lab, tampilkan alasan
            error = str(exc)
    if error or ssrf_preview is not None:
        return _products_page(
            request, db, admin, error=error, ssrf_preview=ssrf_preview,
            status_code=400 if error else 200,
        )
    return RedirectResponse("/admin/products", status_code=303)


# --------------------------------------------------------------------------- #
# Admin tools — network check (target Web-A03-d command injection)
# --------------------------------------------------------------------------- #
@router.get("/tools", response_class=HTMLResponse)
def tools_form(request: Request, admin=Depends(require_admin)):
    return templates.TemplateResponse("admin/tools.html", {"request": request, "user": admin})


@router.post("/tools/ping", response_class=HTMLResponse)
def tools_ping(
    request: Request,
    host: str = Form(...),
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Utilitas 'cek koneksi (ping)'. Web-A03-d mengontrol pemakaian shell."""
    if challenges.enabled("web.Web-A03-d"):
        # LAB-VULN: Web-A03-d command injection (intentional) — input dirakit ke shell.
        cmd = f"ping {_ping_count_flag()} 1 {host}"
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            output = (proc.stdout or "") + (proc.stderr or "")
        except subprocess.SubprocessError as exc:
            output = f"[error] {exc}"
    else:
        # AMAN: allowlist host + argumen list tanpa shell.
        if not _HOST_RE.match(host):
            output = "Host tidak valid (hanya huruf, angka, titik, dan hubung)."
        else:
            try:
                proc = subprocess.run(
                    ["ping", _ping_count_flag(), "1", host],
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                output = (proc.stdout or "") + (proc.stderr or "")
            except (FileNotFoundError, subprocess.SubprocessError) as exc:
                output = f"Utilitas tidak tersedia: {exc}"
    return templates.TemplateResponse(
        "admin/tools.html", {"request": request, "user": admin, "host": host, "output": output}
    )


# --------------------------------------------------------------------------- #
# Mutasi user & order (strict — bukan target batch ini)
# --------------------------------------------------------------------------- #
@router.post("/users/{user_id}/role")
def user_set_role(
    user_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    target = db.get(User, user_id)
    if target and role in {"guest", "customer", "admin"}:
        target.role = role
        db.commit()
        # Web-A09: perubahan peran = aksi sensitif; dicatat hanya bila logging tak "dimatikan".
        audit.log_sensitive("role_change", actor_id=admin.id, target_id=target.id, role=role)
    return RedirectResponse("/admin/users", status_code=303)


@router.post("/orders/{order_id}/status")
def order_set_status(
    order_id: int,
    status_value: str = Form(..., alias="status"),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    order = db.get(Order, order_id)
    if order and status_value in {"pending", "paid", "cancelled"}:
        order.status = status_value
        db.commit()
    return RedirectResponse("/admin/orders", status_code=303)
