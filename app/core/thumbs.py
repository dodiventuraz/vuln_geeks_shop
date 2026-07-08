"""Generator thumbnail dummy untuk produk (inline SVG, tanpa file/CDN).

Menghasilkan tile gradient deterministik (warna dari nama produk) + emoji yang
sesuai jenis barang. Dipakai template saat produk belum punya `image_path`.
"""

from __future__ import annotations

import hashlib
from markupsafe import Markup

# Urutan penting: apparel & item spesifik dicek dulu supaya kata umum (mis. "coffee"
# pada nama kaos) tak salah cocok. Yang lebih spesifik di atas.
_EMOJI_BY_KEYWORD: list[tuple[tuple[str, ...], str]] = [
    (("keyboard", "mechanical"), "⌨️"),
    (("headphone", "headset", "earphone", "earbud"), "🎧"),
    (("webcam", "camera"), "📷"),
    (("mouse",), "🖱️"),
    (("monitor", "display"), "🖥️"),
    (("hub", "usb", "cable", "charger", "adapter"), "🔌"),
    (("hoodie", "jaket", "jacket", "sweater"), "🧥"),
    (("kaos", "shirt", "tshirt", "t-shirt", "tee"), "👕"),
    (("book", "handbook", "code", "buku"), "📘"),
    (("mug", "cup", "coffee"), "☕"),
    (("desk", "meja", "standing", "chair", "kursi"), "🪑"),
    (("phone", "hp", "smartphone"), "📱"),
    (("watch", "jam"), "⌚"),
]

_EMOJI_BY_CATEGORY = {
    "elektronik": "💻",
    "buku": "📚",
    "fashion": "👗",
    "rumah-tangga": "🏠",
}


def _pick_emoji(product) -> str:
    name = (getattr(product, "name", "") or "").lower()
    for keywords, emoji in _EMOJI_BY_KEYWORD:
        if any(k in name for k in keywords):
            return emoji
    category = getattr(product, "category", None)
    slug = getattr(category, "slug", "") if category is not None else ""
    return _EMOJI_BY_CATEGORY.get(slug, "🛍️")


def product_thumbnail(product) -> Markup:
    """Kembalikan markup SVG thumbnail (aman untuk di-render langsung)."""
    seed = (getattr(product, "slug", None) or getattr(product, "name", None) or "x")
    hue = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16) % 360
    c1 = f"hsl({hue},68%,74%)"
    c2 = f"hsl({(hue + 38) % 360},70%,55%)"
    gid = f"pt{getattr(product, 'id', 0)}-{hue}"
    emoji = _pick_emoji(product)
    svg = (
        f'<svg viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" '
        f'xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;display:block">'
        f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>'
        f'</linearGradient></defs>'
        f'<rect width="400" height="300" fill="url(#{gid})"/>'
        f'<circle cx="330" cy="55" r="95" fill="rgba(255,255,255,0.16)"/>'
        f'<circle cx="65" cy="255" r="62" fill="rgba(255,255,255,0.12)"/>'
        f'<text x="200" y="160" font-size="128" text-anchor="middle" '
        f'dominant-baseline="central">{emoji}</text>'
        f'</svg>'
    )
    return Markup(svg)
