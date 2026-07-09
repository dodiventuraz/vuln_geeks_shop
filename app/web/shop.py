"""Route katalog & belanja (SSR): daftar produk, pencarian, kategori, detail,
review, wishlist.

P1 AMAN: pencarian pakai query parameterized (ORM `ilike` dengan bind), review
dirender dengan autoescape Jinja2. Titik SQLi search (Web-A03-a), Reflected/Stored XSS
(Web-A03-b) diberi penanda TODO untuk fase P2.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Template
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.challenges import challenges
from app.core.db import get_db
from app.core.security import get_current_user, require_login
from app.core.templating import templates
from app.models import Category, Product, Review, Wishlist

router = APIRouter(tags=["web-shop"])


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    q: str = "",
    category: str = "",
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    active_category = None
    if category:
        active_category = db.execute(
            select(Category).where(Category.slug == category)
        ).scalar_one_or_none()

    if q and challenges.enabled("web.Web-A03-a"):
        # LAB-VULN: Web-A03-a SQLi search (intentional) — kolom pencarian dirakit mentah.
        sql = text(f"SELECT id FROM products WHERE name LIKE '%{q}%'")  # noqa: S608
        ids = [r.id for r in db.execute(sql).fetchall()]
        products = [db.get(Product, i) for i in ids]
        products = [p for p in products if p is not None]
    else:
        stmt = select(Product)
        if active_category:
            stmt = stmt.where(Product.category_id == active_category.id)
        if q:
            # AMAN: ilike ter-parameter (bind); autoescape template mencegah reflected XSS.
            stmt = stmt.where(Product.name.ilike(f"%{q}%"))
        products = db.execute(stmt.order_by(Product.id)).scalars().all()

    categories = db.execute(select(Category).order_by(Category.name)).scalars().all()
    # Flag hasil eksploitasi (mis. SQLi login) yang di-stash di session.
    flag = request.session.pop("lab_flag", None)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user,
            "products": products,
            "categories": categories,
            "q": q,
            "active_category": active_category,
            "flag": flag,
        },
    )


@router.get("/greeting", response_class=HTMLResponse)
def greeting_form(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("greeting.html", {"request": request, "user": user})


@router.post("/greeting", response_class=HTMLResponse)
def greeting_preview(
    request: Request,
    message: str = Form(...),
    user=Depends(get_current_user),
):
    """Pratinjau "kartu ucapan hadiah".

    Web-A03-c mengontrol apakah pesan user dirender sebagai template Jinja2.
    """
    if challenges.enabled("web.Web-A03-c"):
        # LAB-VULN: Web-A03-c SSTI (intentional) — string user dirender sebagai template.
        # Konteks memuat `flag`, jadi payload `{{ flag }}` membocorkannya; `{{7*7}}` → 49.
        try:
            rendered = Template(message).render(user=user, flag=challenges.flag("web.Web-A03-c"))
        except Exception as exc:  # noqa: BLE001 — lab: tampilkan error render apa adanya
            rendered = f"[render error] {exc}"
    else:
        # AMAN: diperlakukan teks biasa (di-escape saat ditampilkan, tidak dievaluasi).
        rendered = message
    return templates.TemplateResponse(
        "greeting.html", {"request": request, "user": user, "message": message, "rendered": rendered}
    )


@router.get("/product/{product_id}", response_class=HTMLResponse)
def product_detail(
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    product = db.get(Product, product_id)
    if product is None:
        return templates.TemplateResponse(
            "message.html",
            {"request": request, "user": user, "title": "404", "message": "Produk tidak ditemukan."},
            status_code=404,
        )
    reviews = db.execute(
        select(Review).where(Review.product_id == product_id).order_by(Review.created_at.desc())
    ).scalars().all()
    return templates.TemplateResponse(
        "product_detail.html",
        {"request": request, "user": user, "product": product, "reviews": reviews},
    )


@router.post("/product/{product_id}/review")
def add_review(
    product_id: int,
    request: Request,
    rating: int = Form(5),
    body: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    product = db.get(Product, product_id)
    if product is not None:
        # AMAN: body disimpan apa adanya lalu dirender dengan autoescape.
        # TODO[P2] Web-A03-b: Stored XSS dibuka dengan `| safe` di template review (fase P2).
        rating = max(1, min(5, int(rating)))
        db.add(Review(product_id=product_id, user_id=user.id, rating=rating, body=body))
        db.commit()
    return RedirectResponse(f"/product/{product_id}", status_code=303)


# --- Wishlist ---
@router.get("/wishlist", response_class=HTMLResponse)
def wishlist_view(request: Request, db: Session = Depends(get_db), user=Depends(require_login)):
    items = db.execute(select(Wishlist).where(Wishlist.user_id == user.id)).scalars().all()
    return templates.TemplateResponse(
        "wishlist.html", {"request": request, "user": user, "items": items}
    )


@router.post("/wishlist/add")
def wishlist_add(
    product_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    exists = db.execute(
        select(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == product_id)
    ).scalar_one_or_none()
    if exists is None and db.get(Product, product_id) is not None:
        db.add(Wishlist(user_id=user.id, product_id=product_id))
        db.commit()
    return RedirectResponse(f"/product/{product_id}", status_code=303)


@router.post("/wishlist/remove")
def wishlist_remove(
    product_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_login),
):
    item = db.execute(
        select(Wishlist).where(Wishlist.user_id == user.id, Wishlist.product_id == product_id)
    ).scalar_one_or_none()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/wishlist", status_code=303)
