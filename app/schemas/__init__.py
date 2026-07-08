"""Skema Pydantic v2.

P1: skema AMAN & ketat (allowlist field, validasi tipe). Pelonggaran yang disengaja
(mass assignment A-3a, qty negatif W-A04a) baru dibuka di fase P2/P3.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth ---
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=200)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Output (AMAN: field terbatas, tidak membocorkan password_hash/PII) ---
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    role: str


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
    price: Decimal
    stock: int
    category_id: int | None = None


# --- Input business (AMAN: qty dibatasi positif; longgar-nya menyusul di W-A04a) ---
class CartAddIn(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=100)
