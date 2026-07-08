"""Setup SQLAlchemy 2.x: engine, session factory, declarative Base.

P0 hanya menyediakan fondasi koneksi. Belum ada model bisnis di sini.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """Base deklaratif untuk seluruh model SQLAlchemy (diisi mulai P1)."""


def get_db() -> Generator[Session, None, None]:
    """Dependency FastAPI: sediakan sesi DB per-request lalu tutup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
