# PRD — Vuln Geeks Shop: Vulnerable E-Commerce Lab

> **Aplikasi:** Vuln Geeks Shop — aplikasi e-commerce yang *sengaja dibuat rentan* untuk latihan **Web Pentest** & **API Pentest**.
>
> **Status dokumen:** Draft v0.2 · **Tipe:** Training / Security Lab (non-produksi) · **Stack:** Python / FastAPI

---

## ⚠️ Peringatan & Batasan Penggunaan (WAJIB DIBACA)

Vuln Geeks Shop mengandung kerentanan yang disengaja. Karena itu:

- **DILARANG** di-deploy ke internet publik atau jaringan produksi. Jalankan **hanya** di lingkungan terisolasi (localhost, VM lab, jaringan air-gapped, atau Docker network internal).
- **TIDAK** menggunakan data asli, kredensial asli, atau integrasi pembayaran asli. Semua serba *mock*.
- Aplikasi menampilkan **banner peringatan** permanen di UI dan README bahwa ini lab latihan.
- Sertakan **disclaimer legal/etika**: skill yang dilatih hanya untuk pengujian yang diizinkan (authorized testing). Tanpa izin tertulis, pengujian ke sistem milik orang lain adalah ilegal.

---

## 1. Latar Belakang & Tujuan

### 1.1 Latar belakang
Praktisi pentest butuh sandbox yang realistis untuk mengasah teknik tanpa risiko hukum. Lab e-commerce dipilih karena mencakup alur bisnis kaya (auth, keranjang, checkout, pembayaran, admin, API) sehingga bisa memuat spektrum kerentanan luas — dari OWASP Top 10 (web) sampai OWASP API Security Top 10.

### 1.2 Tujuan
1. Menyediakan target latihan **web pentest** yang mencakup OWASP Top 10 2021.
2. Menyediakan permukaan **API pentest** (REST + opsional GraphQL) yang mencakup OWASP API Security Top 10 2023.
3. Bisa **di-deploy 1 perintah** dan **di-reset** ke kondisi bersih.
4. Mendukung level kesulitan bertingkat (beginner → advanced) dengan hint & solution guide terpisah.

### 1.3 Non-goals
- Bukan aplikasi e-commerce siap produksi.
- Bukan platform CTF penuh dengan multi-tenant/leaderboard skala besar (scoreboard opsional, lihat §10).
- Tidak mensimulasikan serangan jaringan/infrastruktur (fokus di lapisan aplikasi & API).

---

## 2. Metrik Keberhasilan

| Metrik | Target |
|---|---|
| Cakupan OWASP Top 10 (web) | 10/10 kategori terwakili |
| Cakupan OWASP API Security Top 10 | 10/10 kategori terwakili |
| Waktu setup dari nol | ≤ 5 menit, 1 perintah |
| Reset ke state bersih | ≤ 30 detik |
| Setiap kerentanan punya | lokasi + objective + hint + solusi terdokumentasi |
| Reproducibility | 100% (seed deterministik) |

---

## 3. Target Pengguna (Personas)

- **Pemula pentest** — baru belajar Burp Suite/DevTools, butuh hint & alur bertahap.
- **Pentester menengah** — ingin latihan chaining vuln & business-logic flaw.
- **Instruktur/mentor** — memakai lab untuk kelas, butuh solution guide & mode reset.
- **Bug bounty hunter** — melatih metodologi API recon & IDOR/BOLA hunting.

---

## 4. Ruang Lingkup

**In scope:** aplikasi web e-commerce full-stack, REST API, opsional GraphQL, admin panel, dokumentasi kerentanan, seed data, mekanisme reset, Docker deployment.

**Out of scope:** integrasi pembayaran nyata, pengiriman email nyata (pakai mailhog/mock), kerentanan level OS/kernel, DDoS.

---

## 5. Kebutuhan Keamanan Lab (Safety Requirements)

Kebutuhan agar labnya *aman dipakai* meski isinya rentan:

- **REQ-S1** Default bind ke `127.0.0.1` (uvicorn `--host 127.0.0.1`); expose ke jaringan hanya lewat flag eksplisit.
- **REQ-S2** Banner "⚠️ INTENTIONALLY VULNERABLE — LAB USE ONLY" di header UI & response header (middleware FastAPI menambahkan `X-Lab-Warning`).
- **REQ-S3** Skrip `reset.sh` / `make reset` mengembalikan DB & file ke state awal.
- **REQ-S4** Seed data deterministik (akun, produk, order contoh) untuk hasil yang konsisten.
- **REQ-S5** Semua "pembayaran" via service gateway mock yang selalu sukses/gagal sesuai skenario.
- **REQ-S6** Tidak ada telemetry/koneksi keluar tak disengaja (kecuali fitur SSRF yang memang disengaja & terkontrol ke target internal lab).

---

## 6. Kebutuhan Fungsional — Aplikasi E-Commerce

Fitur dibuat realistis supaya kerentanan punya konteks bisnis.

### 6.1 Autentikasi & Akun
- Registrasi, login, logout, "lupa password" (reset via token).
- Sesi berbasis **cookie session** (Starlette SessionMiddleware) *dan* endpoint API berbasis **JWT** (PyJWT) — dua permukaan auth.
- Profil user: nama, email, alamat pengiriman, foto avatar (upload).
- Role: `guest`, `customer`, `admin`.

### 6.2 Katalog & Belanja
- Daftar produk, kategori, **pencarian** & filter.
- Halaman detail produk + **review/komentar** user (render via Jinja2).
- **Wishlist**.
- **Keranjang** (tambah/ubah qty/hapus).

### 6.3 Checkout & Order
- Checkout dengan alamat + metode bayar (mock).
- **Kupon/diskon**.
- Riwayat order, detail order, **invoice/receipt** (HTML/PDF).

### 6.4 Admin Panel
- CRUD produk, kelola user, kelola order, lihat laporan.
- Upload gambar produk.
- Fitur "import produk dari URL" (kandidat SSRF, via `requests`/`httpx`).

### 6.5 API
- REST API terversion (`/api/v1`, `/api/v2`) untuk semua alur di atas (FastAPI routers).
- Opsional **GraphQL** endpoint (Strawberry atau Ariadne).
- Dokumentasi API otomatis FastAPI (`/docs` Swagger UI, `/openapi.json`) — sebagian sengaja bocor/misconfig.

---

## 7. Katalog Kerentanan yang Disengaja (Inti PRD)

Setiap entri: **lokasi**, **mekanisme (versi Python)**, dan **level**. Semua toggle-able via config `challenges.yaml`.

### 7.1 Web — OWASP Top 10 (2021)

| ID | Kategori | Kerentanan & Mekanisme Python | Level |
|---|---|---|---|
| W-A01a | Broken Access Control | **IDOR** `/orders/{id}` & `/invoice/{id}` — query by id tanpa cek `current_user` | Easy |
| W-A01b | Broken Access Control | Forced browsing ke `/admin` — dependency auth tidak dipasang di router admin | Medium |
| W-A01c | Broken Access Control | Missing function-level check pada endpoint hapus/ubah produk | Medium |
| W-A02a | Cryptographic Failures | Password di-hash lemah (`hashlib.md5`, tanpa salt) alih-alih bcrypt/argon2 | Easy |
| W-A02b | Cryptographic Failures | PII/kartu mock tersimpan plaintext di DB | Medium |
| W-A03a | Injection | **SQLi** di login & search — raw query `text(f"... {input}")` / string-format ke SQLAlchemy | Easy→Hard |
| W-A03b | Injection | **Stored XSS** di review (`| safe` di Jinja2); **Reflected XSS** di hasil search | Easy |
| W-A03c | Injection | **SSTI** — input user dimasukkan ke `Template(...).render()` Jinja2 | Hard |
| W-A03d | Injection | **Command injection** di tools admin — `subprocess.run(cmd, shell=True)` / `os.system` | Hard |
| W-A04a | Insecure Design | **Business logic**: qty negatif → total negatif; validasi Pydantic sengaja longgar | Medium |
| W-A04b | Insecure Design | **Race condition** kupon/stock (TOCTOU) di checkout async tanpa lock | Hard |
| W-A05a | Security Misconfiguration | `debug=True`, stack trace verbose, error handler bocor detail | Easy |
| W-A05b | Security Misconfiguration | `.git/` ter-expose, StaticFiles serve direktori, file `.bak`/`.env` terjangkau | Easy |
| W-A05c | Security Misconfiguration | **CORSMiddleware** longgar (`allow_origins=["*"]` + `allow_credentials=True`), security header hilang | Medium |
| W-A06 | Vulnerable Components | Dependency versi lama ber-CVE di-pin di `requirements.txt` | Medium |
| W-A07a | Auth Failures | Tanpa rate limit → **brute force** login/OTP (slowapi sengaja tidak dipasang) | Easy |
| W-A07b | Auth Failures | Session fixation / token reset password predictable (`random` bukan `secrets`) | Hard |
| W-A08 | Integrity Failures | **Insecure deserialization** (`pickle.loads` / `yaml.load` unsafe); JWT `alg:none` / secret lemah | Hard |
| W-A09 | Logging Failures | Aksi sensitif tak ter-log; tak ada deteksi anomali (untuk diamati) | Info |
| W-A10 | SSRF | "Import gambar dari URL" — `httpx.get(user_url)` menembak service internal | Medium |

### 7.2 API — OWASP API Security Top 10 (2023)

| ID | Kategori | Kerentanan & Mekanisme Python | Level |
|---|---|---|---|
| A-1 | **BOLA** | `GET /api/v1/orders/{id}` ambil object by id tanpa cek kepemilikan | Easy |
| A-2 | Broken Authentication | PyJWT verify menerima `alg:none`/secret lemah; refresh token tak divalidasi | Medium |
| A-3a | Broken Object **Property** Level Auth | **Mass assignment**: `PATCH /api/user` pakai `Model(**payload)` → set `role/balance/verified` | Medium |
| A-3b | Excessive Data Exposure | Response pakai schema penuh (bocor `password_hash`/PII) alih-alih response_model terbatas | Easy |
| A-4 | Unrestricted Resource Consumption | Tanpa rate limit & tanpa batas pagination (`?limit=999999` diterima) | Easy |
| A-5 | Broken Function Level Auth | User biasa bisa panggil `POST /api/v1/admin/...` (dependency role tak dipasang) | Medium |
| A-6 | Unrestricted Access to Business Flows | Beli item "limited" massal / spam kupon lewat API | Medium |
| A-7 | SSRF | Endpoint webhook/URL-fetch di API (`httpx`/`requests`) | Medium |
| A-8 | Security Misconfiguration | `/docs` & `/openapi.json` ter-expose penuh, error verbose, method berlebih | Easy |
| A-9 | **Improper Inventory Management** | `/api/v1` lawas masih aktif & lebih rentan dari `/api/v2`; endpoint undocumented | Medium |
| A-10 | Unsafe Consumption of 3rd-party API | Data dari payment-mock dipercaya mentah tanpa validasi | Hard |

### 7.3 Kerentanan chaining (bonus, level advanced)
- IDOR (A-1) + Mass assignment (A-3a) → **privilege escalation** ke admin.
- SSRF (W-A10) → akses service metadata internal lab → ambil kredensial → akses admin API.
- Reflected XSS + CORS longgar → **pencurian token JWT** via API.

---

## 8. Arsitektur & Tech Stack

### 8.1 Stack (final: Python / FastAPI)
- **Bahasa/Framework:** Python 3.11+ · **FastAPI** (REST) · **Uvicorn** (ASGI server).
- **ORM/DB:** SQLAlchemy 2.x + **PostgreSQL** (Alembic untuk migrasi opsional).
- **Auth:** Starlette `SessionMiddleware` (cookie) + **PyJWT** (token API).
- **Template/SSR:** **Jinja2** (untuk halaman web + titik XSS/SSTI).
- **Validasi:** Pydantic v2 (sengaja dilonggarkan di titik business-logic/mass-assignment).
- **HTTP client:** `httpx` (untuk fitur SSRF terkontrol).
- **GraphQL (opsional):** Strawberry atau Ariadne.
- **Frontend:** server-rendered Jinja2 + sedikit JS; boleh SPA terpisah bila diinginkan.

### 8.2 Struktur proyek (usulan)
```
vuln-geeks-shop/
├── app/
│   ├── main.py              # FastAPI app, middleware, mount routers
│   ├── core/                # config, security (JWT/session), db session
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── api/
│   │   ├── v1/              # router lama (lebih rentan)
│   │   └── v2/              # router baru
│   ├── web/                 # route SSR + templates Jinja2
│   ├── graphql/             # (opsional) Strawberry schema
│   └── challenges.py        # loader challenges.yaml (toggle vuln)
├── seed/                    # data seed deterministik
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── Makefile
├── challenges.yaml
├── README.md
├── CHALLENGES.md
└── SOLUTIONS.md
```

### 8.3 Komponen runtime
```
[ Browser / Burp ] ──▶ [ FastAPI (Uvicorn) SSR + REST v1/v2 ]
                                   │            │
                                   ▼            ▼
                          [ GraphQL (opt) ]  [ PostgreSQL ]
                                   │
                                   ▼
                   [ internal-metadata service (target SSRF) ]
                   [ Mailhog (email mock) ]
                   [ payment-mock service ]
```

### 8.4 Deployment
- **Docker Compose** dengan service: `app` (FastAPI/Uvicorn), `db` (Postgres), `mailhog`, `internal-metadata`, `payment-mock`.
- Perintah: `docker compose up` → siap. `make reset` → seed ulang DB & file.
- Network internal Docker; hanya `app` yang expose port ke `127.0.0.1`.

---

## 9. Kebutuhan Non-Fungsional

- **NFR-1 Deployability:** jalan lintas OS via Docker.
- **NFR-2 Reproducibility:** seed deterministik, versi dependency di-pin di `requirements.txt`.
- **NFR-3 Reset:** state bisa dikembalikan bersih kapan saja (`make reset`).
- **NFR-4 Dokumentasi:** README + `CHALLENGES.md` + `SOLUTIONS.md` (terpisah/terkunci).
- **NFR-5 Konfigurabilitas:** tiap kerentanan on/off via `challenges.yaml`.
- **NFR-6 Observability lab:** log request (middleware) agar efek serangan bisa diamati.

---

## 10. Struktur Pembelajaran (Challenge Design)

- **Tier kesulitan:** Beginner / Intermediate / Advanced.
- **Hint bertingkat:** 3 level hint per tantangan (nudge → arah → langkah).
- **Solution guide:** file `SOLUTIONS.md` terpisah (branch/zip berpassword) agar tak spoiler.
- **(Opsional) Scoreboard/Flag:** tiap vuln menaruh "flag" yang hanya muncul setelah eksploitasi berhasil + endpoint submit flag sederhana. Bisa dimatikan untuk mode free-form.
- **Peta pembelajaran:** mapping tantangan → OWASP → tool (Burp, sqlmap, ffuf, jwt_tool, Postman/httpie).

---

## 11. Deliverables

1. Source code (FastAPI web + API) di repo Git.
2. `docker-compose.yml` + `Dockerfile` + `Makefile` (up/reset/down).
3. Seed data & skrip reset.
4. `README.md` (setup + peringatan).
5. `CHALLENGES.md` (daftar tantangan + objective + hint).
6. `SOLUTIONS.md` (walkthrough — terpisah).
7. `challenges.yaml` (toggle vuln).
8. OpenAPI spec (otomatis dari FastAPI di `/openapi.json`).

---

## 12. Roadmap / Milestone

| Fase | Isi | Estimasi |
|---|---|---|
| **P0 — Fondasi** | Scaffold FastAPI, SQLAlchemy models, auth, Docker, seed, reset | Minggu 1 |
| **P1 — Fitur e-commerce** | Katalog, cart, checkout, order, admin, upload (SSR Jinja2) | Minggu 2 |
| **P2 — Vuln Web** | Implement W-A01…W-A10 + loader `challenges.yaml` | Minggu 3 |
| **P3 — API + Vuln API** | Router REST v1/v2, (GraphQL), A-1…A-10, konfigurasi `/docs` | Minggu 4 |
| **P4 — Dokumentasi & polish** | CHALLENGES/SOLUTIONS, hint, (scoreboard), QA reproducibility | Minggu 5 |

---

## 13. Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Lab ter-expose ke publik & disalahgunakan | Bind localhost default, banner peringatan, dokumentasi tegas |
| Vuln "bocor" tak sengaja ke sistem lain | Isolasi Docker network, tanpa koneksi keluar tak disengaja |
| Kerentanan tak konsisten (flaky) | Seed deterministik + `make reset` + QA per rilis |
| Solusi ter-spoiler | `SOLUTIONS.md` dipisah/dienkripsi |
| Dependency CVE jadi usang | Versi rentan di-pin sengaja & didokumentasikan |

---

## 14. Referensi & Proyek Sejenis

- OWASP Top 10 (2021) & OWASP API Security Top 10 (2023) — kerangka acuan kerentanan.
- Pembanding berbasis Python yang bagus dipelajari polanya: **crAPI**, **VAmPI** (keduanya fokus API), serta **OWASP Juice Shop**, **DVWA**, **WebGoat** sebagai referensi umum.

---

### Lampiran A — Contoh `challenges.yaml`
```yaml
web:
  A01_idor_orders: { enabled: true, level: easy, flag: "FLAG{idor_orders}" }
  A03_sqli_login:  { enabled: true, level: easy }
  A03_ssti_jinja2: { enabled: false, level: hard }
  A10_ssrf_import: { enabled: false, level: medium }
api:
  BOLA_orders:        { enabled: true, level: easy }
  mass_assignment:    { enabled: true, level: medium }
  improper_inventory: { enabled: true, level: medium }
```

### Lampiran B — Contoh `requirements.txt` (versi sengaja di-pin)
```
fastapi
uvicorn[standard]
sqlalchemy>=2.0
psycopg2-binary
jinja2
pydantic>=2
pyjwt
httpx
python-multipart        # upload file
itsdangerous            # session
pyyaml                  # dipakai di titik deserialization
# catatan: beberapa paket akan sengaja di-pin ke versi ber-CVE (didokumentasikan di SOLUTIONS.md)
```
