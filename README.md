# Vuln Geeks Shop

> ## ⚠️ INTENTIONALLY VULNERABLE — LAB USE ONLY
> Aplikasi e-commerce yang **sengaja dibuat rentan** untuk latihan **Web Pentest** & **API Pentest**.
> Ini **lab edukasi non-produksi** (sepadan dengan OWASP Juice Shop / crAPI / DVWA).
> **Kerentanan di sini adalah fitur, bukan bug.**

---

## 🚫 Peringatan & Disclaimer

- **DILARANG** men-deploy aplikasi ini ke internet publik atau jaringan produksi.
  Jalankan **hanya** di lingkungan terisolasi (localhost, VM lab, atau jaringan internal Docker).
- Aplikasi **default bind ke `127.0.0.1`** dan hanya service `app` yang dipublikasikan ke host.
- Semua layanan eksternal (email, payment) adalah **mock**. Tidak ada data / kredensial / pembayaran asli.
- **Authorized testing only.** Skill yang dilatih di sini hanya untuk pengujian yang **diizinkan**.
  Menguji sistem milik pihak lain tanpa izin tertulis adalah **ilegal**.

---

## 📦 Status

**Fase: P4 — Dokumentasi & polish.** Aplikasi e-commerce fungsional (katalog, cart, checkout
payment-mock, order/invoice, review, wishlist, profil, admin panel) + REST API v1/v2, dengan
kerentanan yang bisa di-toggle lewat `challenges.yaml`.

| Cakupan | Status |
|---|---|
| **Web — OWASP Top 10 (2021)** | **20/20 kategori aktif** (W-A01a … W-A10) ✅ |
| **API — OWASP API Top 10 (2023)** | **4/11 entri aktif** (A-1, A-2, A-3b, A-9) — sisanya backlog ⚠️ |
| Setiap vuln punya | dua cabang (rentan/aman) via toggle, flag, exploit-test |

> **Kerentanan di sini DISENGAJA.** Tiap titik rentan diberi penanda `# LAB-VULN: <id> (intentional)`
> dan bercabang `if challenges.enabled("<id>"): <rentan> else: <aman>`. Detail per challenge di
> `CHALLENGES.md`; walkthrough di `SOLUTIONS.md` (gitignored).
>
> ⚠️ **Backlog P3:** A-3a (mass assignment), A-4 (resource consumption), A-5 (function-level authz),
> A-6 (business-flow abuse), A-7 (SSRF API), A-8 (misconfig `/docs`), A-10 (unsafe 3rd-party) belum
> diimplementasikan (`enabled: false`). GraphQL (opsional PRD §6.5) juga backlog.

## 👤 Akun Seed (untuk login)

Dibuat oleh `make seed` / `make reset` (deterministik):

| Email | Password | Role |
|---|---|---|
| `admin@vulnshop.lab` | `Admin123!` | admin |
| `alice@vulnshop.lab` | `Password123` | customer (punya order contoh) |
| `bob@vulnshop.lab` | `Password123` | customer (punya order contoh) |
| `carol@vulnshop.lab` | `Password123` | customer (belum terverifikasi) |

Seed juga mengisi 4 kategori, 10 produk, 3 kupon (`WELCOME10`, `SAVE20`, `EXPIRED`), dan 2 order contoh.

---

## 🧰 Tech Stack

Python 3.11+ · FastAPI · Uvicorn · SQLAlchemy 2.x · PostgreSQL · Jinja2 · PyJWT · httpx · Docker Compose.

---

## 🚀 Menjalankan (Docker)

Prasyarat: Docker + Docker Compose.

```bash
make up        # build & jalankan seluruh lab (app, db, mailhog, stub internal)
make seed      # isi data awal deterministik (WAJIB setelah `up` pertama kali)
make logs      # ikuti log app
make down      # hentikan
make reset     # kembalikan DB & file ke state bersih, lalu seed ulang
make test      # jalankan pytest di dalam container
```

Alur pertama kali: `make up` lalu `make seed` (atau langsung `make reset`). Skema tabel dibuat
otomatis saat app start; `make seed` mengisi akun & produk. App tersedia di
**http://127.0.0.1:8000** · UI Mailhog di **http://127.0.0.1:8025**.

### Cek /health

```bash
curl http://127.0.0.1:8000/health
```

Contoh respons (DB terhubung):

```json
{
  "status": "ok",
  "app": "Vuln Geeks Shop",
  "version": "0.0.1-p0",
  "env": "dev",
  "warning": "INTENTIONALLY VULNERABLE — LAB USE ONLY",
  "database": { "ok": true, "error": null },
  "challenges_loaded": true
}
```

Setiap respons juga membawa header **`X-Lab-Warning: INTENTIONALLY VULNERABLE — LAB USE ONLY`**.

## 🧪 Menjalankan lokal (tanpa Docker)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # sesuaikan DATABASE_URL bila perlu
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

> `/health` tetap mengembalikan `200` meski DB belum aktif (status `degraded` + detail error),
> sehingga cocok untuk smoke test.

---

## 📁 Struktur Repo

```
app/
  main.py            # FastAPI app, middleware, exception handler, mount router, /health
  core/              # config, db, security, net(SSRF), payments, ratelimit, audit, scoreboard, challenges
  models/            # 11 model SQLAlchemy (User, Product, Order, dst.)
  schemas/           # Pydantic v2 (auth, token, output terbatas)
  services.py        # logika bisnis (cart, checkout, kupon/TOCTOU)
  api/v1/  api/v2/   # REST API (v1 lebih rentan, v2 lebih aman) + deps/serializers
  web/               # router SSR + templates/ Jinja2 + static/
seed/                # seed deterministik (akun, produk, order contoh)
lab_files/           # artefak "bocor" untuk W-A05b (data palsu)
tests/               # fungsional + exploit-test per vuln (web & API) + scoreboard
challenges.yaml      # toggle kerentanan (web 20/20 aktif, api 4/11 aktif)
docker-compose.yml  Dockerfile  Makefile  requirements.txt  pytest.ini
PRD.md  CLAUDE.md  CHALLENGES.md   (SOLUTIONS.md → gitignored)
```

---

## 🎯 Cara Main

1. Buka **http://127.0.0.1:8000**, login pakai akun seed (lihat tabel di atas).
2. Baca objective & hint tiap tantangan di **`CHALLENGES.md`** (termasuk peta pembelajaran → OWASP → tool).
3. Eksploitasi → dapatkan **`FLAG{...}`** → submit di **`/scoreboard`** untuk melacak progres.
4. Nyalakan/matikan tantangan lewat **`challenges.yaml`** (mendukung latihan bertahap Easy→Hard).
5. REST API: ambil token via `POST /api/v1/auth/token` (JSON `{email,password}`), pakai header
   `Authorization: Bearer <token>`. Swagger UI di **`/docs`**, spec di **`/openapi.json`**.

---

## ✅ Checklist Rilis (PRD §2)

| Metrik | Target | Status |
|---|---|---|
| Cakupan OWASP Top 10 (web) | 10/10 kategori | ✅ 10/10 (20 sub-challenge) |
| Cakupan OWASP API Top 10 | 10/10 kategori | ⚠️ 4/11 entri aktif (sisanya backlog) |
| Setup dari nol | ≤ 5 menit, 1 perintah | ✅ `make up` + `make seed` |
| Reset ke state bersih | ≤ 30 detik | ✅ `make reset` (seed drop+create, deterministik) |
| Seed deterministik | 100% | ✅ terverifikasi (snapshot identik antar-run) |
| Tiap vuln punya lokasi+objective+hint+solusi | ya | ✅ (untuk yang aktif) |
| Exploit-test per vuln aktif | lulus | ✅ `make test` hijau |
| Banner + `X-Lab-Warning` | wajib | ✅ |
| Bind 127.0.0.1, no outbound tak disengaja | wajib | ✅ (outbound hanya fitur SSRF terkontrol) |
| `SOLUTIONS.md` tidak ter-commit | wajib | ✅ di `.gitignore` |

---

## 📚 Dokumentasi

- **`PRD.md`** — spesifikasi lengkap & katalog kerentanan.
- **`CLAUDE.md`** — aturan main proyek (kontrak kerja).
- **`CHALLENGES.md`** — daftar tantangan + hint + peta pembelajaran (tanpa jawaban, aman dibagikan).
- **`SOLUTIONS.md`** — walkthrough/kunci jawaban (**gitignored**, jangan dibagikan ke peserta).
