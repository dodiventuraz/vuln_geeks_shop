"""Fixture pytest bersama.

Tes fungsional memakai SQLite in-memory (shared) lewat override dependency get_db,
sehingga tidak butuh PostgreSQL aktif. Skema dibuat dari metadata model yang sama.
"""

from __future__ import annotations

import copy
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — daftarkan model ke metadata sebelum create_all
from app.core.challenges import challenges
from app.core.db import Base, get_db
from app.main import app as fastapi_app

# --- Engine SQLite in-memory bersama untuk seluruh sesi test ---
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Skema bersih per test."""
    from app.core import audit, promo, ratelimit

    Base.metadata.create_all(bind=_engine)
    fastapi_app.dependency_overrides[get_db] = _override_get_db
    ratelimit.clear_all()
    audit.clear()
    promo.clear()
    yield
    fastapi_app.dependency_overrides.clear()
    ratelimit.clear_all()
    audit.clear()
    promo.clear()
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(autouse=True)
def _isolate_challenges():
    """Isolasi state challenges per test.

    Default: SEMUA challenge dipaksa OFF, sehingga test fungsional P1 melihat
    perilaku AMAN terlepas dari isi challenges.yaml. Exploit-test P2 memakai
    fixture `enable_challenge` untuk menyalakan yang diuji.
    """
    saved = copy.deepcopy(challenges._data)
    for section in challenges._data.values():
        if isinstance(section, dict):
            for entry in section.values():
                if isinstance(entry, dict):
                    entry["enabled"] = False
    yield
    challenges._data = saved


@pytest.fixture()
def enable_challenge():
    def _enable(dotted_key: str) -> None:
        section, cid = dotted_key.split(".", 1)
        challenges._data.setdefault(section, {}).setdefault(cid, {})["enabled"] = True

    return _enable


@pytest.fixture()
def client() -> TestClient:
    return TestClient(fastapi_app)


@pytest.fixture()
def error_client() -> TestClient:
    # Tidak re-raise server exception, agar respons 500 (verbose/generic) bisa diperiksa.
    return TestClient(fastapi_app, raise_server_exceptions=False)


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def sample_product(db):
    """Sisipkan 1 kategori + produk dan kembalikan produk."""
    from app.models import Category, Product

    cat = Category(name="Test", slug="test")
    db.add(cat)
    db.flush()
    product = Product(name="Test Product", slug="test-product", price=Decimal("10.00"), stock=5, category_id=cat.id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture()
def registered_client(client) -> TestClient:
    """Client yang sudah register + login (cookie session terpasang)."""
    client.post(
        "/register",
        data={"email": "tester@vulnshop.lab", "name": "Tester", "password": "Password123"},
        follow_redirects=False,
    )
    return client
