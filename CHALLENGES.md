# CHALLENGES.md — Vuln Geeks Shop

Daftar tantangan latihan untuk lab ini. **File ini tidak memuat jawaban** — aman di-commit.
Walkthrough & perbaikan ada di `SOLUTIONS.md` (dipisah / gitignored — lihat CLAUDE.md).

## Cara pakai
1. Nyalakan/matikan tantangan lewat `challenges.yaml`.
2. Kerjakan sesuai urutan level bila kamu pemula (Easy → Hard).
3. Buka hint bertahap: coba **Hint 1** dulu, baru turun ke bawah kalau mentok.
4. Bukti keberhasilan = kamu mendapatkan **flag** (format `FLAG{...}`) atau efek yang dijelaskan di objective.

## Legend level
🟢 Easy · 🟡 Medium · 🔴 Hard · ⚪ Info (untuk diamati, bukan dieksploitasi)

## Tool yang relevan
Burp Suite / DevTools · `sqlmap` · `ffuf` · `jwt_tool` · Postman / `httpie` · `curl`

---

## Bagian A — Web (OWASP Top 10 2021)

### W-A01a · IDOR pada Order/Invoice 🟢
- **Lokasi:** `GET /orders/{id}`, `GET /invoice/{id}` · toggle `web.W-A01a`
- **Objective:** Akses order/invoice milik user lain tanpa izin.
- **Hint 1:** Perhatikan angka pada URL saat kamu membuka order sendiri.
- **Hint 2:** Apa yang terjadi kalau angka itu kamu ubah?
- **Hint 3:** Bandingkan: apakah server mengecek bahwa order itu benar milikmu?

### W-A01b · Akses Admin Tanpa Role 🟡
- **Lokasi:** `GET /admin` (juga `/admin/products`, `/admin/users`, `/admin/orders`) · toggle `web.W-A01b`
- **Objective:** Masuk area admin sebagai user biasa (login sebagai customer, lalu buka path admin langsung).
- **Hint 1:** Tautan admin tak muncul di UismU-mu — tapi apakah route-nya benar-benar tertutup?
- **Hint 2:** Coba akses path admin secara langsung.
- **Hint 3:** Cek apakah proteksi role dipasang di setiap route admin, atau ada yang terlewat.

### W-A01c · Aksi Terlarang di Produk 🟡
- **Lokasi:** `POST /admin/products/{id}/update`, `POST /admin/products/{id}/delete` · toggle `web.W-A01c`
- **Objective:** Lakukan aksi mutasi produk (khusus admin) sebagai user biasa.
- **Hint 1:** UI menyembunyikan tombol — apakah backend juga?
- **Hint 2:** Amati request yang dikirim admin (method + endpoint).
- **Hint 3:** Kirim request setara sebagai user biasa.

### W-A02a · Hash Password Lemah 🟢
- **Lokasi:** penyimpanan kredensial (registrasi/reset); hash bocor di `GET /profile` · toggle `web.W-A02a`
- **Objective:** Buktikan hash password bisa dibalik/di-crack dengan mudah.
- **Hint 1:** Kalau kamu punya akses ke nilai hash, kenali formatnya.
- **Hint 2:** Panjang & karakter hash memberi tahu algoritmanya.
- **Hint 3:** Algoritma cepat tanpa salt = rentan rainbow table / cracking.

### W-A02b · Data Sensitif Plaintext 🟡
- **Lokasi:** kartu pembayaran mock — `POST /profile/billing`, tampil di `GET /profile` · toggle `web.W-A02b`
- **Objective:** Temukan data sensitif (PAN kartu) yang tersimpan tanpa enkripsi/tokenisasi.
- **Hint 1:** Tidak semua data sensitif itu password.
- **Hint 2:** Telusuri data yang bocor lewat vuln lain (mis. IDOR/SQLi).
- **Hint 3:** Perhatikan apakah nilai tersimpan apa adanya.

### W-A03a · SQL Injection (Login & Search) 🟢→🔴
- **Lokasi:** `POST /login` (field email), `GET /?q=` (pencarian produk) · toggle `web.W-A03a`
- **Objective:** Bypass login dan/atau ekstraksi data lewat query.
- **Hint 1:** Apa yang terjadi bila input memuat karakter kutip?
- **Hint 2:** Amati pesan error atau perubahan hasil.
- **Hint 3:** Naik level: dari bypass ke ekstraksi (pertimbangkan `sqlmap`).

### W-A03b · XSS (Stored & Reflected) 🟢
- **Lokasi:** stored → `POST /product/{id}/review` (body review); reflected → `GET /?q=` · toggle `web.W-A03b`
- **Objective:** Jalankan skrip di browser korban (mis. curi `window.LAB_XSS_FLAG`).
- **Hint 1:** Ke mana input-mu ditampilkan kembali?
- **Hint 2:** Apakah karakter HTML di-escape?
- **Hint 3:** Stored bertahan di halaman; reflected lewat parameter URL.

### W-A03c · Server-Side Template Injection 🔴
- **Lokasi:** `POST /greeting` (kartu ucapan; link "Kartu" di navbar) · toggle `web.W-A03c`
- **Objective:** Eksekusi ekspresi di server lewat template.
- **Hint 1:** Coba masukkan ekspresi matematis sederhana dalam kurung kurawal.
- **Hint 2:** Kalau hasilnya "dihitung", input-mu masuk ke mesin template.
- **Hint 3:** Dari evaluasi ekspresi, telusuri akses ke objek/atribut.

### W-A03d · Command Injection 🔴
- **Lokasi:** `POST /admin/tools/ping` (Admin → Tools → Cek koneksi) · toggle `web.W-A03d`
- **Objective:** Jalankan perintah OS lewat input aplikasi (butuh akses admin; bisa dirantai dengan W-A01b).
- **Hint 1:** Fitur mana yang tampak memanggil utilitas sistem?
- **Hint 2:** Karakter apa yang memisahkan/menyambung perintah shell?
- **Hint 3:** Uji dengan perintah tidak merusak dulu (mis. cetak identitas).

### W-A04a · Business Logic: Qty Negatif 🟡
- **Lokasi:** `POST /cart/add` (field `quantity`) → `POST /checkout` · toggle `web.W-A04a`
- **Objective:** Manipulasi total agar tidak wajar (negatif).
- **Hint 1:** Apakah kuantitas divalidasi rentang-nya?
- **Hint 2:** Apa efek angka negatif terhadap total?
- **Hint 3:** Kirim nilai lewat request langsung, bukan lewat UI.

### W-A04b · Race Condition Kupon/Stock 🔴
- **Lokasi:** `POST /coupon/redeem` (kirim banyak request paralel) · toggle `web.W-A04b`
- **Objective:** Pakai kupon melebihi batas (`max_uses`) via race.
- **Hint 1:** Batas dicek kapan — sebelum atau saat commit?
- **Hint 2:** Apa yang terjadi bila banyak request tiba nyaris bersamaan?
- **Hint 3:** Kirim request paralel (race) untuk mengeksploitasi jendela TOCTOU.

### W-A05a · Misconfig: Verbose Error / Debug 🟢
- **Lokasi:** halaman error 500 (picu contoh: `GET /debug/error`) · toggle `web.W-A05a`
- **Objective:** Bocorkan detail internal lewat error.
- **Hint 1:** Picu error yang tak tertangani.
- **Hint 2:** Apa yang ditampilkan halaman error?
- **Hint 3:** Stack trace membocorkan path, versi, dan kadang query.

### W-A05b · File & Path Ter-expose 🟢
- **Lokasi:** `GET /assets/{path}` (mis. `/assets/.env.bak`, `/assets/config.php.bak`) · toggle `web.W-A05b`
- **Objective:** Temukan file yang seharusnya tak publik (dotfile/backup/traversal).
- **Hint 1:** Ada artefak version control yang bocor?
- **Hint 2:** Coba tebak file cadangan/konfig umum.
- **Hint 3:** Gunakan `ffuf` untuk fuzz path & ekstensi umum.

### W-A05c · CORS Longgar & Header Hilang 🟡
- **Lokasi:** middleware CORS/security (berlaku semua respons; cek dengan header `Origin`) · toggle `web.W-A05c`
- **Objective:** Tunjukkan origin lain bisa membaca respons ber-kredensial.
- **Hint 1:** Cek header respons terkait CORS.
- **Hint 2:** Apakah wildcard dipakai bersama credentials?
- **Hint 3:** Susun bukti request lintas-origin.

### W-A06 · Komponen Rentan (CVE) 🟡
- **Lokasi:** dependency proyek (`requirements.txt`); versi bocor di `GET /debug/deps` · toggle `web.W-A06`
- **Objective:** Identifikasi paket ber-CVE yang dipakai.
- **Hint 1:** Cek daftar dependency & versinya.
- **Hint 2:** Cocokkan versi dengan basis data CVE.
- **Hint 3:** Kaitkan CVE dengan permukaan yang bisa dijangkau di app.

### W-A07a · Tanpa Rate Limit → Brute Force 🟢
- **Lokasi:** `POST /login` · toggle `web.W-A07a`
- **Objective:** Tebak kredensial via percobaan berulang (tanpa dibatasi/dikunci).
- **Hint 1:** Apakah ada pembatasan jumlah percobaan?
- **Hint 2:** Otomatisasi percobaan dengan wordlist.
- **Hint 3:** Amati perbedaan respons untuk membedakan benar/salah.

### W-A07b · Token Reset Predictable / Session Fixation 🔴
- **Lokasi:** `POST /forgot` → `POST /reset` (token); sesi login tak diregenerasi · toggle `web.W-A07b`
- **Objective:** Ambil alih akun via token reset yang bisa diprediksi.
- **Hint 1:** Bagaimana token reset dibangkitkan?
- **Hint 2:** Sumber acak yang lemah bisa diprediksi.
- **Hint 3:** Untuk fixation: bisakah ID sesi ditetapkan sebelum login?

### W-A08 · Insecure Deserialization / JWT Lemah 🔴
- **Lokasi:** `POST /preferences/import` (blob YAML) · toggle `web.W-A08` · (JWT `alg:none` menyusul di API/P3)
- **Objective:** Sisipkan objek ter-serialisasi yang dipercaya mentah (eksekusi callable).
- **Hint 1:** Data apa yang di-*decode*/*load* dari input pengguna?
- **Hint 2:** Untuk JWT: cek algoritma yang diterima server.
- **Hint 3:** Pertimbangkan `jwt_tool` untuk menguji kelemahan tanda tangan.

### W-A09 · Logging & Monitoring ⚪
- **Lokasi:** audit log aksi sensitif (login sukses, ubah peran admin) · toggle `web.W-A09`
- **Objective:** (Amati) aksi sensitif tidak tercatat/terdeteksi saat toggle aktif.
- **Hint 1:** Lakukan aksi sensitif, lalu periksa log.
- **Hint 2:** Apa yang absen di log?
- **Hint 3:** Diskusikan dampaknya terhadap deteksi insiden.

### W-A10 · SSRF via Import URL 🟡
- **Lokasi:** `POST /admin/products/{id}/import-image` (field `image_url`) · toggle `web.W-A10`
- **Objective:** Paksa server meminta ke tujuan internal (mis. service `internal-metadata`).
- **Hint 1:** Siapa yang melakukan request — browser atau server?
- **Hint 2:** Bisakah kamu arahkan ke alamat internal lab?
- **Hint 3:** Incar service metadata/internal yang hanya terjangkau server.

---

## Bagian B — API (OWASP API Security Top 10 2023)

### A-1 · BOLA (IDOR di API) 🟢
- **Lokasi:** `GET /api/v1/orders/{id}` (aman: `GET /api/v2/orders/{id}`) · toggle `api.A-1`
- **Objective:** Baca object (order) milik user lain lewat API.
- **Hint 1:** Object direferensikan dengan id yang bisa ditebak.
- **Hint 2:** Ganti id ke milik user lain.
- **Hint 3:** Apakah server memverifikasi kepemilikan?

### A-2 · Broken Authentication (JWT) 🟡
- **Lokasi:** verifikasi token API v1 (uji di `GET /api/v1/me`; aman: `GET /api/v2/me`) · toggle `api.A-2`
- **Objective:** Lewati autentikasi dengan token palsu (`alg:none`).
- **Hint 1:** Periksa header & algoritma JWT.
- **Hint 2:** Apakah `alg` lemah/`none` diterima?
- **Hint 3:** Uji apakah tanda tangan benar-benar diverifikasi.

### A-3a · Mass Assignment 🟡
- **Lokasi:** `PATCH /api/user`
- **Objective:** Set properti yang seharusnya tak boleh diubah user.
- **Hint 1:** Field apa yang dikembalikan objek user?
- **Hint 2:** Coba kirim field tambahan di body.
- **Hint 3:** Incar properti berhak-istimewa (mis. peran/saldo/verifikasi).

### A-3b · Excessive Data Exposure 🟢
- **Lokasi:** `GET /api/v1/users/{id}` (aman: `GET /api/v2/users/{id}`) · toggle `api.A-3b`
- **Objective:** Temukan data sensitif (password_hash/PII) yang ikut terkirim di respons.
- **Hint 1:** Baca respons JSON dengan teliti.
- **Hint 2:** Apakah ada field yang seharusnya internal?
- **Hint 3:** Bandingkan data-mu vs data user lain.

### A-4 · Unrestricted Resource Consumption 🟢
- **Lokasi:** endpoint list/paginasi
- **Objective:** Bebani/serobot data lewat parameter tanpa batas.
- **Hint 1:** Apakah `limit`/`page` dibatasi?
- **Hint 2:** Coba nilai yang sangat besar.
- **Hint 3:** Amati apakah tidak ada rate limit.

### A-5 · Broken Function Level Authorization 🟡
- **Lokasi:** `POST /api/v1/admin/...`
- **Objective:** Panggil fungsi admin sebagai user biasa.
- **Hint 1:** Endpoint admin ada di dokumentasi API?
- **Hint 2:** Coba panggil dengan token user biasa.
- **Hint 3:** Cek apakah pengecekan peran terpasang di endpoint itu.

### A-6 · Unrestricted Access to Business Flows 🟡
- **Lokasi:** alur beli/kupon via API
- **Objective:** Salahgunakan alur bisnis (borong item limited / spam kupon).
- **Hint 1:** Alur mana yang mengandaikan "pemakaian manusiawi"?
- **Hint 2:** Otomatisasi alur itu.
- **Hint 3:** Adakah pembatasan kecepatan/kuota?

### A-7 · SSRF (API) 🟡
- **Lokasi:** endpoint webhook/URL-fetch
- **Objective:** Buat server memanggil tujuan pilihanmu.
- **Hint 1:** Endpoint mana yang menerima URL?
- **Hint 2:** Arahkan ke internal lab.
- **Hint 3:** Serupa W-A10, tapi lewat API.

### A-8 · Security Misconfiguration (API) 🟢
- **Lokasi:** `/docs`, `/openapi.json`, header/method
- **Objective:** Manfaatkan konfigurasi API yang terlalu terbuka.
- **Hint 1:** Apakah dokumentasi API terbuka publik?
- **Hint 2:** Endpoint apa yang terungkap dari sana?
- **Hint 3:** Coba method HTTP yang tak diharapkan.

### A-9 · Improper Inventory Management 🟡
- **Lokasi:** `/api/v1` (lawas) vs `/api/v2`; endpoint undocumented `GET /api/v1/_debug/orders` · toggle `api.A-9`
- **Objective:** Temukan versi/endpoint lama yang lebih rentan & tak terdokumentasi.
- **Hint 1:** Ada lebih dari satu versi API?
- **Hint 2:** Bandingkan perilaku v1 vs v2 untuk aksi yang sama.
- **Hint 3:** Cari endpoint yang tak terdokumentasi.

### A-10 · Unsafe Consumption of 3rd-party API 🔴
- **Lokasi:** integrasi payment-mock
- **Objective:** Manfaatkan kepercayaan buta terhadap respons pihak ketiga.
- **Hint 1:** Data apa dari gateway yang langsung dipercaya?
- **Hint 2:** Bisakah respons itu kamu pengaruhi?
- **Hint 3:** Apa dampaknya bila server tak memvalidasinya?

---

## Catatan flag
Flag muncul hanya setelah eksploitasi berhasil, format `FLAG{...}`. Submit di **`/scoreboard`**
untuk mencatat progres. Daftar flag & mapping ada di `challenges.yaml` (untuk instruktur).
Jangan bagikan `SOLUTIONS.md` ke peserta yang sedang mengerjakan lab.

---

## Peta Pembelajaran (Challenge → OWASP → Tool)

Status: ✅ aktif (implemented + enabled) · 🚧 rencana (belum diimplementasikan).

### Web — OWASP Top 10 (2021)
| Challenge | Kategori OWASP | Tool relevan | Status |
|---|---|---|---|
| W-A01a IDOR order/invoice | A01 Broken Access Control | Burp, DevTools | ✅ |
| W-A01b Forced admin | A01 Broken Access Control | Burp, ffuf | ✅ |
| W-A01c Product mutation | A01 Broken Access Control | Burp, curl | ✅ |
| W-A02a Weak md5 hash | A02 Cryptographic Failures | hashcat, john | ✅ |
| W-A02b Plaintext PII | A02 Cryptographic Failures | Burp (chain IDOR/SQLi) | ✅ |
| W-A03a SQL Injection | A03 Injection | sqlmap, Burp | ✅ |
| W-A03b XSS (stored/reflected) | A03 Injection | Browser, Burp | ✅ |
| W-A03c SSTI (Jinja2) | A03 Injection | tplmap, Burp | ✅ |
| W-A03d Command Injection | A03 Injection | commix, Burp | ✅ |
| W-A04a Qty negatif | A04 Insecure Design | Burp, curl | ✅ |
| W-A04b Race kupon (TOCTOU) | A04 Insecure Design | Burp Turbo Intruder | ✅ |
| W-A05a Verbose error/debug | A05 Security Misconfiguration | Browser, Burp | ✅ |
| W-A05b File & path ter-expose | A05 Security Misconfiguration | ffuf, dirsearch | ✅ |
| W-A05c CORS longgar | A05 Security Misconfiguration | Burp, PoC HTML | ✅ |
| W-A06 Komponen ber-CVE | A06 Vulnerable Components | pip-audit, OSV, safety | ✅ |
| W-A07a Brute force | A07 Auth Failures | Hydra, Burp Intruder | ✅ |
| W-A07b Predictable token | A07 Auth Failures | Script kustom, Burp | ✅ |
| W-A08 Insecure deserialization | A08 Integrity Failures | Burp, payload YAML | ✅ |
| W-A09 Logging & monitoring | A09 Logging Failures | Observasi log | ✅ |
| W-A10 SSRF via import URL | A10 SSRF | Burp, curl | ✅ |

### API — OWASP API Security Top 10 (2023)
| Challenge | Kategori OWASP API | Tool relevan | Status |
|---|---|---|---|
| A-1 BOLA | API1 BOLA | Burp, Postman/httpie | ✅ |
| A-2 Broken Auth (JWT) | API2 Broken Authentication | jwt_tool | ✅ |
| A-3a Mass Assignment | API3 Broken Object Property Level Auth | Burp, Postman | 🚧 |
| A-3b Excessive Data Exposure | API3 Broken Object Property Level Auth | Burp, httpie | ✅ |
| A-4 Unrestricted Resource Consumption | API4 | Burp, curl | 🚧 |
| A-5 Broken Function Level Auth | API5 | Postman, Burp | 🚧 |
| A-6 Business Flow Abuse | API6 | Script kustom | 🚧 |
| A-7 SSRF (API) | API7 | Burp, curl | 🚧 |
| A-8 Security Misconfiguration | API8 | Browser (`/docs`), Burp | 🚧 |
| A-9 Improper Inventory Mgmt | API9 | ffuf, banding v1/v2 | ✅ |
| A-10 Unsafe 3rd-party Consumption | API10 | Burp, payment-mock | 🚧 |
