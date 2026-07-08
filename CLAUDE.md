# CLAUDE.md — Vuln Geeks Shop

File ini adalah aturan main proyek untuk Claude Code. Baca sebelum menulis kode apa pun.
Referensi lengkap ada di `PRD.md` — file ini adalah versi "kontrak kerja" yang lebih padat.

---

## 1. Apa proyek ini

**Vuln Geeks Shop** adalah aplikasi e-commerce yang **SENGAJA DIBUAT RENTAN**, untuk latihan
Web Pentest & API Pentest. Ini **lab edukasi non-produksi**, sepadan dengan OWASP Juice Shop / crAPI / DVWA.

> ⚠️ **Kerentanan di sini adalah fitur, bukan bug.** Jangan pernah "memperbaiki"-nya kecuali diminta eksplisit.

---

## 2. Aturan Wajib (NON-NEGOTIABLE)

1. **Kerentanan itu disengaja — JANGAN ditambal.** Saat mengimplementasikan endpoint/fitur yang ada di
   katalog kerentanan (PRD §7), tulis versi rentannya sesuai deskripsi. Jangan menambahkan sanitasi,
   parameterized query, auth check, atau validasi yang menutup vuln yang dimaksud. Kalau ragu apakah suatu
   kelemahan disengaja, **berhenti dan tanya**, jangan diam-diam mengamankan.
2. **Isolasi lab.** App default bind ke `127.0.0.1` (uvicorn `--host 127.0.0.1`). Jangan pernah set
   default ke `0.0.0.0` atau expose ke jaringan publik. Semua layanan eksternal (email, payment) adalah
   **mock**. Tidak boleh ada koneksi keluar yang tak disengaja — satu-satunya "outbound" yang boleh hanya
   fitur SSRF yang memang disengaja dan menembak service internal lab.
3. **Pisahkan solusi.** `SOLUTIONS.md` **tidak boleh** di-commit ke branch utama (masuk `.gitignore` atau
   branch/zip terpisah). `CHALLENGES.md` (tanpa jawaban) boleh.
4. **Banner peringatan wajib ada.** UI menampilkan banner "INTENTIONALLY VULNERABLE — LAB USE ONLY", dan
   middleware menambahkan response header `X-Lab-Warning`.
5. **Reproducibility.** Seed data harus deterministik. `make reset` harus mengembalikan DB & file ke state
   bersih. Jangan menambah fitur yang merusak dua hal ini.
6. **Data palsu saja.** Tidak ada PII asli, kredensial asli, atau data pembayaran asli di seed maupun kode.

---

## 3. Tech Stack (final)

- Python 3.11+ · **FastAPI** · **Uvicorn** (ASGI)
- **SQLAlchemy 2.x** + **PostgreSQL** (Alembic opsional)
- Auth: Starlette `SessionMiddleware` (cookie, untuk web) + **PyJWT** (token, untuk API)
- SSR: **Jinja2** (sekaligus titik XSS/SSTI)
- Validasi: Pydantic v2 (sengaja dilonggarkan di titik business-logic / mass-assignment)
- HTTP client: `httpx` (untuk fitur SSRF terkontrol)
- GraphQL (opsional, fase belakang): Strawberry/Ariadne
- Deploy: Docker Compose

Jangan ganti stack atau menambah framework berat tanpa persetujuan.

---

## 4. Perintah Proyek

```bash
make up       # docker compose up — jalankan seluruh lab
make down     # hentikan
make reset    # seed ulang DB & file ke state bersih
make seed     # isi data awal (deterministik)
make test     # jalankan pytest (termasuk exploit-test, lihat §6)
```

Kalau perintah ini belum ada di fase awal, buatlah — ini bagian dari fondasi P0.

---

## 5. Struktur Repo (target)

```
app/
  main.py            # FastAPI app, middleware (CORS, session, X-Lab-Warning), mount routers
  core/              # config, security (JWT/session), db session, challenges loader
  models/            # SQLAlchemy models
  schemas/           # Pydantic schemas
  api/v1/            # router lama (versi lebih rentan)
  api/v2/            # router baru
  web/               # route SSR + templates Jinja2
  graphql/           # (opsional) Strawberry schema
seed/                # data seed deterministik
tests/               # termasuk exploit-test per kerentanan
challenges.yaml      # toggle kerentanan (lihat §7)
docker-compose.yml  Dockerfile  Makefile  requirements.txt
PRD.md  CLAUDE.md  README.md  CHALLENGES.md   (SOLUTIONS.md → gitignored)
```

---

## 6. Cara Menambah Kerentanan (Definition of Done)

Untuk **setiap** item di PRD §7, sebuah kerentanan dianggap "selesai" hanya jika keempatnya terpenuhi:

1. **Implement** jalur rentannya sesuai mekanisme di PRD (mis. SQLi via raw `text(f"...")`,
   SSTI via `Template(...).render()`, mass assignment via `Model(**payload)`).
2. **Toggle** lewat `challenges.yaml` — endpoint memilih jalur rentan/aman berdasarkan flag.
3. **Dokumentasi:** tambahkan entri di `CHALLENGES.md` (lokasi + objective + hint bertingkat), dan
   langkah eksploitasi di `SOLUTIONS.md`.
4. **Exploit-test:** tambahkan test di `tests/` yang **membuktikan** vuln bisa dieksploitasi
   (mis. IDOR mengembalikan data user lain → test `assert` berhasil). Ini menjaga vuln tidak tak sengaja
   "ketambal" saat refactor.

---

## 7. Pola `challenges.yaml` (KONTRAK antar fitur)

Setiap kerentanan bisa dinyalakan/dimatikan. Pola bacanya seragam:

```yaml
web:
  A01_idor_orders: { enabled: true, level: easy, flag: "FLAG{idor_orders}" }
  A03_sqli_login:  { enabled: true, level: easy }
api:
  BOLA_orders:     { enabled: true, level: easy }
  mass_assignment: { enabled: true, level: medium }
```

Di kode, endpoint bercabang berdasarkan flag, contoh pola yang diharapkan:

```python
if challenges.enabled("web.A03_sqli_login"):
    # jalur RENTAN — sesuai desain lab
    rows = db.execute(text(f"SELECT * FROM users WHERE email = '{email}'"))
else:
    # jalur aman — parameterized
    rows = db.execute(text("SELECT * FROM users WHERE email = :e"), {"e": email})
```

Selalu sediakan **kedua cabang**. Ini bukan basa-basi keamanan — ini yang membuat lab bisa dipakai bertahap.

---

## 8. Urutan Kerja (kerjakan PER FASE, jangan sekaligus)

Ikuti roadmap PRD §12. Selesaikan satu fase, tunggu review, baru lanjut.

- **P0 — Fondasi:** scaffold FastAPI + Postgres + Docker Compose + `/health` + `make up/reset`.
  **Belum ada fitur bisnis maupun kerentanan.**
- **P1 — Fitur e-commerce:** katalog, cart, checkout, order, admin, upload — semua **fungsional & aman dulu**.
- **P2 — Vuln Web:** implement W-A01…W-A10 + loader `challenges.yaml`.
- **P3 — API + Vuln API:** router v1/v2, (GraphQL), A-1…A-10, konfigurasi `/docs`.
- **P4 — Dokumentasi & polish:** CHALLENGES/SOLUTIONS, hint, (scoreboard opsional), QA reproducibility.

**Jangan** melompat ke depan atau menghasilkan banyak fase sekaligus. Buat perubahan bertahap dan
bisa direview.

---

## 9. Konvensi

- Utamakan kode yang **jelas dan mudah dibaca** — ini alat belajar, bukan kode produksi. Vuln harus
  terlihat "wajar", bukan disembunyikan berlapis-lapis.
- Beri komentar penanda di titik rentan, mis. `# LAB-VULN: A03 SQLi (intentional)`, agar mudah ditelusuri
  instruktur. (Penanda ini boleh; yang tak boleh adalah menambalnya.)
- Commit kecil dan deskriptif, per kerentanan / per fitur.
- Jangan tambah dependency baru tanpa alasan yang dicatat (khusus paket ber-CVE yang di-pin sengaja untuk
  W-A06, dokumentasikan di `SOLUTIONS.md`).

---

## 10. Yang TIDAK Boleh Dilakukan

- ❌ Menambal/menghardening kerentanan yang ada di katalog PRD §7.
- ❌ Meng-commit `SOLUTIONS.md` ke branch utama.
- ❌ Set default bind ke `0.0.0.0` atau menambah koneksi keluar tak disengaja.
- ❌ Menambahkan integrasi eksternal asli (pembayaran/email nyata).
- ❌ Mengerjakan banyak fase sekaligus tanpa review.
- ❌ Mengganti stack/arsitektur inti tanpa persetujuan.
