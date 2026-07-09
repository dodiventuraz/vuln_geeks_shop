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

## 📦 Status & Cakupan

Aplikasi e-commerce fungsional (katalog, cart, checkout payment-mock, order/invoice, review,
wishlist, profil, admin panel) + REST API v1/v2, dengan kerentanan yang bisa di-toggle lewat
`challenges.yaml`.

| Cakupan | Status |
|---|---|
| **Web — OWASP Top 10 (2021)** | **20/20 kategori aktif** (W-A01a … W-A10) ✅ |
| **API — OWASP API Top 10 (2023)** | **4/11 entri aktif** (A-1, A-2, A-3b, A-9) — sisanya backlog ⚠️ |
| Setiap vuln punya | dua cabang (rentan/aman) via toggle, flag, exploit-test |

> **Kerentanan di sini DISENGAJA.** Tiap titik rentan diberi penanda `# LAB-VULN: <id> (intentional)`
> dan bercabang `if challenges.enabled("<id>"): <rentan> else: <aman>`. Detail per challenge di
> `CHALLENGES.md`; walkthrough di `SOLUTIONS.md` (gitignored).
>
> ⚠️ **Backlog:** A-3a (mass assignment), A-4 (resource consumption), A-5 (function-level authz),
> A-6 (business-flow abuse), A-7 (SSRF API), A-8 (misconfig `/docs`), A-10 (unsafe 3rd-party) belum
> diimplementasikan (`enabled: false`). GraphQL (opsional) juga backlog.

## 👤 Akun Seed (untuk login)

Dibuat saat seeding (langkah 3 pada tutorial Docker), deterministik:

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

## 🚀 Menjalankan Lab dengan Docker Compose

Cara yang direkomendasikan — menjalankan lab lengkap (Postgres, mailhog, service internal target SSRF) dengan satu perintah.

### Prasyarat
- **Docker Desktop** (Windows/macOS) atau **Docker Engine + plugin Compose** (Linux).
- Pastikan Docker sudah aktif — di Docker Desktop tunggu status **"Engine running"**.

> Perintah di bawah pakai `docker compose` (portabel di semua OS). Kalau kamu punya `make`
> (umumnya Linux/macOS), ada shortcut-nya di bagian bawah. Di Windows biasanya `make` tidak
> tersedia, jadi pakai `docker compose` langsung.

### 1. Clone repo
```bash
git clone https://github.com/dodiventuraz/vuln_geeks_shop.git
cd vuln_geeks_shop
```

### 2. Build & jalankan semua service
```bash
docker compose up --build -d
```
Build pertama kali ~3–8 menit (install dependency + pull image). Service yang dijalankan:

| Service | Peran | Publikasi ke host |
|---|---|---|
| `app` | FastAPI/Uvicorn — web SSR + REST API | **127.0.0.1:8099** |
| `db` | PostgreSQL 16 | — (internal saja) |
| `mailhog` | mock email + UI | **127.0.0.1:8025** |
| `internal-metadata` | target SSRF internal (W-A10 / A-7) | — (internal saja) |
| `payment-mock` | gateway pembayaran mock | — (internal saja) |

> **Isolasi:** hanya `app` (+ UI mailhog) yang dipetakan ke `127.0.0.1`. Selebihnya hanya
> ada di jaringan internal Docker — tidak terjangkau dari luar.

### 3. Isi data awal (WAJIB dijalankan sekali di awal)
```bash
docker compose run --rm app python -m seed.seed
```
Skema tabel dibuat otomatis saat `app` start; perintah ini mengisi akun, produk, kupon, dan order contoh (deterministik).

### 4. Buka di browser
- Toko & admin: **http://127.0.0.1:8099**
- Swagger API (OpenAPI): **http://127.0.0.1:8099/docs**
- Mailhog (email masuk): **http://127.0.0.1:8025**

Login pakai akun seed (lihat tabel **Akun Seed** di atas), mis. `admin@vulnshop.lab` / `Admin123!`.

Cek kesehatan app + koneksi DB:
```bash
curl http://127.0.0.1:8099/health
# {"status":"ok", ... ,"database":{"ok":true,...}}
```
Setiap respons membawa header **`X-Lab-Warning: INTENTIONALLY VULNERABLE - LAB USE ONLY`**.

### Perintah harian
```bash
docker compose ps                 # status service
docker compose logs -f app        # ikuti log app (Ctrl+C untuk keluar)
docker compose down               # hentikan (data DB tetap)
docker compose down -v            # hentikan + hapus data DB (bersih total)

# reset ke state bersih (buang data, rebuild, seed ulang):
docker compose down -v; docker compose up --build -d; docker compose run --rm app python -m seed.seed

# jalankan test suite di dalam container:
docker compose run --rm app pytest -q
```

### Shortcut `make` (opsional, jika `make` tersedia)
```bash
make up      # = docker compose up --build -d
make seed    # isi data awal
make logs    # ikuti log app
make down    # hentikan
make reset   # kembalikan ke state bersih + seed ulang
make test    # pytest di dalam container
```

### Troubleshooting
- **`error ... the docker daemon is not running`** → Docker Desktop belum siap; tunggu "Engine running", lalu ulangi.
- **Port `8099`/`8025` sudah dipakai** → hentikan proses lain, atau ubah mapping port di `docker-compose.yml`.
- **Halaman error / katalog kosong** → lupa seed; jalankan langkah 3.
- **Habis mengubah kode** → `docker compose up --build -d` untuk rebuild image `app`.
- **`docker compose up --build -d` "senyap"** → `-d` = detached (background); itu normal. Cek dengan `docker compose ps`. Hilangkan `-d` untuk melihat log build langsung.

---

## 🧪 Alternatif: menjalankan tanpa Docker (SQLite)

Cocok untuk sekadar melihat UI dengan cepat. Butuh Python 3.11+.

```bash
python -m venv .venv
# aktifkan: Linux/macOS → source .venv/bin/activate ; Windows → .venv\Scripts\activate
pip install -r requirements.txt

# pakai SQLite lokal (tanpa Postgres):
# Linux/macOS:
export DATABASE_URL="sqlite:///./labdev.db"
# Windows PowerShell:
#   $env:DATABASE_URL = "sqlite:///./labdev.db"

python -m seed.seed
uvicorn app.main:app --host 127.0.0.1 --port 8099
```

> Catatan: mode ini tanpa mailhog & service SSRF internal. Untuk lab penuh, pakai Docker Compose.

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
README.md  CHALLENGES.md   (SOLUTIONS.md → gitignored, tidak di-publish)
```

---

## 🎯 Cara Main

1. Buka **http://127.0.0.1:8099**, login pakai akun seed (lihat tabel di atas).
2. Baca objective & hint tiap tantangan di **`CHALLENGES.md`** (termasuk peta pembelajaran → OWASP → tool).
3. Eksploitasi → dapatkan **`FLAG{...}`** → submit di **`/scoreboard`** untuk melacak progres.
4. Nyalakan/matikan tantangan lewat **`challenges.yaml`** (mendukung latihan bertahap Easy→Hard).
5. REST API: ambil token via `POST /api/v1/auth/token` (JSON `{email,password}`), pakai header
   `Authorization: Bearer <token>`. Swagger UI di **`/docs`**, spec di **`/openapi.json`**.

---

## ✅ Checklist Rilis

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

- **`README.md`** — setup, cara menjalankan, cara main (file ini).
- **`CHALLENGES.md`** — daftar tantangan + objective + hint bertingkat + peta pembelajaran (challenge → OWASP → tool). Tanpa jawaban, aman dibagikan ke peserta.
- **`challenges.yaml`** — toggle tiap kerentanan (on/off) beserta level & flag.
- **`SOLUTIONS.md`** — walkthrough/kunci jawaban. **Gitignored & tidak di-publish** ke repo — hanya untuk instruktur.
- **`/docs`** — Swagger UI (OpenAPI) untuk permukaan REST API, otomatis dari FastAPI.
