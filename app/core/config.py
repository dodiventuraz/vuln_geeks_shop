"""Konfigurasi aplikasi (dibaca dari environment).

Semua nilai punya default yang aman untuk lab lokal. Bind default ke 127.0.0.1
sesuai CLAUDE.md §2 / PRD REQ-S1 — JANGAN diubah ke 0.0.0.0.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Metadata aplikasi ---
    app_name: str = "Vuln Geeks Shop"
    app_env: str = Field(default="dev", description="dev | test | ci")
    # P0: belum ada kerentanan. debug tetap konservatif di fase ini.
    debug: bool = False

    # --- Server bind (REQ-S1: default localhost, jangan 0.0.0.0) ---
    host: str = "127.0.0.1"
    port: int = 8099

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg2://vuln:vuln@localhost:5432/vulnshop",
        description="SQLAlchemy DSN untuk PostgreSQL.",
    )

    # --- Session / cookie (Starlette SessionMiddleware) ---
    # Nilai lab default; override lewat env di lingkungan nyata (yang mana pun harus tetap isolasi lab).
    session_secret: str = "lab-only-insecure-session-secret-change-me"

    # --- JWT (jalur API, PyJWT) ---
    jwt_secret: str = "lab-only-insecure-jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- Path filesystem ---
    upload_dir: str = "data/uploads"
    templates_dir: str = "app/web/templates"
    static_dir: str = "app/web/static"

    # --- Password hashing (P1: AMAN — pbkdf2-hmac stdlib, salted) ---
    pbkdf2_iterations: int = 260000

    # --- Payment gateway mock (REQ-S5). Kosong = fallback deterministik lokal. ---
    payment_mock_url: str = ""

    # --- CORS (placeholder AMAN di P0; pelonggaran W-A05c menyusul di P2) ---
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:8099"])

    # --- Challenges toggle file ---
    challenges_file: str = "challenges.yaml"

    # --- Banner peringatan lab (REQ-S2) ---
    # Versi UI/body memakai em-dash. Versi header WAJIB ASCII/latin-1 (batasan HTTP header),
    # jadi pakai hyphen biasa untuk X-Lab-Warning.
    lab_warning: str = "INTENTIONALLY VULNERABLE — LAB USE ONLY"
    lab_warning_header: str = "INTENTIONALLY VULNERABLE - LAB USE ONLY"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
