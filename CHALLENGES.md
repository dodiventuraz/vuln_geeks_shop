# CHALLENGES.md — Vuln Geeks Shop

Daftar tantangan latihan untuk lab ini. **File ini tidak memuat jawaban** — aman di-commit.
Walkthrough & perbaikan ada di `SOLUTIONS.md` (terpisah & gitignored — hanya untuk instruktur, tidak di-publish ke repo).

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

### Web-A01-a · IDOR pada Order/Invoice 🟢
- **Lokasi:** `GET /orders/{id}`, `GET /invoice/{id}` · toggle `web.Web-A01-a`
- **Objective:** Akses order/invoice milik user lain tanpa izin.
- **Hint 1:** Perhatikan angka pada URL saat kamu membuka order sendiri.
- **Hint 2:** Apa yang terjadi kalau angka itu kamu ubah?
- **Hint 3:** Bandingkan: apakah server mengecek bahwa order itu benar milikmu?

### Web-A01-b · Akses Admin Tanpa Role 🟡
- **Lokasi:** `GET /admin` (juga `/admin/products`, `/admin/users`, `/admin/orders`) · toggle `web.Web-A01-b`
- **Objective:** Masuk area admin sebagai user biasa (login sebagai customer, lalu buka path admin langsung).
- **Hint 1:** Tautan admin tak muncul di UismU-mu — tapi apakah route-nya benar-benar tertutup?
- **Hint 2:** Coba akses path admin secara langsung.
- **Hint 3:** Cek apakah proteksi role dipasang di setiap route admin, atau ada yang terlewat.

### Web-A01-c · Aksi Terlarang di Produk 🟡
- **Lokasi:** `POST /admin/products/{id}/update`, `POST /admin/products/{id}/delete` · toggle `web.Web-A01-c`
- **Objective:** Lakukan aksi mutasi produk (khusus admin) sebagai user biasa.
- **Hint 1:** UI menyembunyikan tombol — apakah backend juga?
- **Hint 2:** Amati request yang dikirim admin (method + endpoint).
- **Hint 3:** Kirim request setara sebagai user biasa.

### Web-A02-a · Hash Password Lemah 🟢
- **Lokasi:** penyimpanan kredensial (registrasi/reset); hash bocor di `GET /profile` · toggle `web.Web-A02-a`
- **Objective:** Buktikan hash password bisa dibalik/di-crack dengan mudah.
- **Hint 1:** Kalau kamu punya akses ke nilai hash, kenali formatnya.
- **Hint 2:** Panjang & karakter hash memberi tahu algoritmanya.
- **Hint 3:** Algoritma cepat tanpa salt = rentan rainbow table / cracking.

### Web-A02-b · Data Sensitif Plaintext 🟡
- **Lokasi:** kartu pembayaran mock — `POST /profile/billing`, tampil di `GET /profile` · toggle `web.Web-A02-b`
- **Objective:** Temukan data sensitif (PAN kartu) yang tersimpan tanpa enkripsi/tokenisasi.
- **Hint 1:** Tidak semua data sensitif itu password.
- **Hint 2:** Telusuri data yang bocor lewat vuln lain (mis. IDOR/SQLi).
- **Hint 3:** Perhatikan apakah nilai tersimpan apa adanya.

### Web-A03-a · SQL Injection (Login & Search) 🟢→🔴
- **Lokasi:** `POST /login` (field email), `GET /?q=` (pencarian produk) · toggle `web.Web-A03-a`
- **Objective:** Bypass login dan/atau ekstraksi data lewat query.
- **Hint 1:** Apa yang terjadi bila input memuat karakter kutip?
- **Hint 2:** Amati pesan error atau perubahan hasil.
- **Hint 3:** Naik level: dari bypass ke ekstraksi (pertimbangkan `sqlmap`).

### Web-A03-b · XSS (Stored & Reflected) 🟢
- **Lokasi:** stored → `POST /product/{id}/review` (body review); reflected → `GET /?q=` · toggle `web.Web-A03-b`
- **Objective:** Jalankan skrip di browser korban (mis. curi `window.LAB_XSS_FLAG`).
- **Hint 1:** Ke mana input-mu ditampilkan kembali?
- **Hint 2:** Apakah karakter HTML di-escape?
- **Hint 3:** Stored bertahan di halaman; reflected lewat parameter URL.

### Web-A03-c · Server-Side Template Injection 🔴
- **Lokasi:** `POST /greeting` (kartu ucapan; link "Kartu" di navbar) · toggle `web.Web-A03-c`
- **Objective:** Eksekusi ekspresi di server lewat template.
- **Hint 1:** Coba masukkan ekspresi matematis sederhana dalam kurung kurawal.
- **Hint 2:** Kalau hasilnya "dihitung", input-mu masuk ke mesin template.
- **Hint 3:** Dari evaluasi ekspresi, telusuri akses ke objek/atribut.

### Web-A03-d · Command Injection 🔴
- **Lokasi:** `POST /admin/tools/ping` (Admin → Tools → Cek koneksi) · toggle `web.Web-A03-d`
- **Objective:** Jalankan perintah OS lewat input aplikasi (butuh akses admin; bisa dirantai dengan Web-A01-b).
- **Hint 1:** Fitur mana yang tampak memanggil utilitas sistem?
- **Hint 2:** Karakter apa yang memisahkan/menyambung perintah shell?
- **Hint 3:** Uji dengan perintah tidak merusak dulu (mis. cetak identitas).

### Web-A04-a · Business Logic: Qty Negatif 🟡
- **Lokasi:** `POST /cart/add` (field `quantity`) → `POST /checkout` · toggle `web.Web-A04-a`
- **Objective:** Manipulasi total agar tidak wajar (negatif).
- **Hint 1:** Apakah kuantitas divalidasi rentang-nya?
- **Hint 2:** Apa efek angka negatif terhadap total?
- **Hint 3:** Kirim nilai lewat request langsung, bukan lewat UI.

### Web-A04-b · Race Condition Kupon/Stock 🔴
- **Lokasi:** `POST /coupon/redeem` (kirim banyak request paralel) · toggle `web.Web-A04-b`
- **Objective:** Pakai kupon melebihi batas (`max_uses`) via race.
- **Hint 1:** Batas dicek kapan — sebelum atau saat commit?
- **Hint 2:** Apa yang terjadi bila banyak request tiba nyaris bersamaan?
- **Hint 3:** Kirim request paralel (race) untuk mengeksploitasi jendela TOCTOU.

### Web-A05-a · Misconfig: Verbose Error / Debug 🟢
- **Lokasi:** halaman error 500 (picu contoh: `GET /debug/error`) · toggle `web.Web-A05-a`
- **Objective:** Bocorkan detail internal lewat error.
- **Hint 1:** Picu error yang tak tertangani.
- **Hint 2:** Apa yang ditampilkan halaman error?
- **Hint 3:** Stack trace membocorkan path, versi, dan kadang query.

### Web-A05-b · File & Path Ter-expose 🟢
- **Lokasi:** `GET /assets/{path}` (mis. `/assets/.env.bak`, `/assets/config.php.bak`) · toggle `web.Web-A05-b`
- **Objective:** Temukan file yang seharusnya tak publik (dotfile/backup/traversal).
- **Hint 1:** Ada artefak version control yang bocor?
- **Hint 2:** Coba tebak file cadangan/konfig umum.
- **Hint 3:** Gunakan `ffuf` untuk fuzz path & ekstensi umum.

### Web-A05-c · CORS Longgar & Header Hilang 🟡
- **Lokasi:** middleware CORS/security (berlaku semua respons; cek dengan header `Origin`) · toggle `web.Web-A05-c`
- **Objective:** Tunjukkan origin lain bisa membaca respons ber-kredensial.
- **Hint 1:** Cek header respons terkait CORS.
- **Hint 2:** Apakah wildcard dipakai bersama credentials?
- **Hint 3:** Susun bukti request lintas-origin.

### Web-A06 · Komponen Rentan (CVE) 🟡
- **Lokasi:** dependency proyek (`requirements.txt`); versi bocor di `GET /debug/deps` · toggle `web.Web-A06`
- **Objective:** Identifikasi paket ber-CVE yang dipakai.
- **Hint 1:** Cek daftar dependency & versinya.
- **Hint 2:** Cocokkan versi dengan basis data CVE.
- **Hint 3:** Kaitkan CVE dengan permukaan yang bisa dijangkau di app.

### Web-A07-a · Tanpa Rate Limit → Brute Force 🟢
- **Lokasi:** `POST /login` · toggle `web.Web-A07-a`
- **Objective:** Tebak kredensial via percobaan berulang (tanpa dibatasi/dikunci).
- **Hint 1:** Apakah ada pembatasan jumlah percobaan?
- **Hint 2:** Otomatisasi percobaan dengan wordlist.
- **Hint 3:** Amati perbedaan respons untuk membedakan benar/salah.

### Web-A07-b · Token Reset Predictable / Session Fixation 🔴
- **Lokasi:** `POST /forgot` → `POST /reset` (token); sesi login tak diregenerasi · toggle `web.Web-A07-b`
- **Objective:** Ambil alih akun via token reset yang bisa diprediksi.
- **Hint 1:** Bagaimana token reset dibangkitkan?
- **Hint 2:** Sumber acak yang lemah bisa diprediksi.
- **Hint 3:** Untuk fixation: bisakah ID sesi ditetapkan sebelum login?

### Web-A08 · Insecure Deserialization / JWT Lemah 🔴
- **Lokasi:** `POST /preferences/import` (blob YAML) · toggle `web.Web-A08` · (JWT `alg:none` menyusul di API/P3)
- **Objective:** Sisipkan objek ter-serialisasi yang dipercaya mentah (eksekusi callable).
- **Hint 1:** Data apa yang di-*decode*/*load* dari input pengguna?
- **Hint 2:** Untuk JWT: cek algoritma yang diterima server.
- **Hint 3:** Pertimbangkan `jwt_tool` untuk menguji kelemahan tanda tangan.

### Web-A09 · Logging & Monitoring ⚪
- **Lokasi:** audit log aksi sensitif (login sukses, ubah peran admin) · toggle `web.Web-A09`
- **Objective:** (Amati) aksi sensitif tidak tercatat/terdeteksi saat toggle aktif.
- **Hint 1:** Lakukan aksi sensitif, lalu periksa log.
- **Hint 2:** Apa yang absen di log?
- **Hint 3:** Diskusikan dampaknya terhadap deteksi insiden.

### Web-A10 · SSRF via Import URL 🟡
- **Lokasi:** `POST /admin/products/{id}/import-image` (field `image_url`) · toggle `web.Web-A10`
- **Objective:** Paksa server meminta ke tujuan internal (mis. service `internal-metadata`).
- **Hint 1:** Siapa yang melakukan request — browser atau server?
- **Hint 2:** Bisakah kamu arahkan ke alamat internal lab?
- **Hint 3:** Incar service metadata/internal yang hanya terjangkau server.

---

## Bagian B — API (OWASP API Security Top 10 2023)

### API-A1 · BOLA (IDOR di API) 🟢
- **Lokasi:** `GET /api/v1/orders/{id}` (aman: `GET /api/v2/orders/{id}`) · toggle `api.API-A1`
- **Objective:** Baca object (order) milik user lain lewat API.
- **Hint 1:** Object direferensikan dengan id yang bisa ditebak.
- **Hint 2:** Ganti id ke milik user lain.
- **Hint 3:** Apakah server memverifikasi kepemilikan?

### API-A2 · Broken Authentication (JWT) 🟡
- **Lokasi:** verifikasi token API v1 (uji di `GET /api/v1/me`; aman: `GET /api/v2/me`) · toggle `api.API-A2`
- **Objective:** Lewati autentikasi dengan token palsu (`alg:none`).
- **Hint 1:** Periksa header & algoritma JWT.
- **Hint 2:** Apakah `alg` lemah/`none` diterima?
- **Hint 3:** Uji apakah tanda tangan benar-benar diverifikasi.

### API-A3-a · Mass Assignment 🟡
- **Lokasi:** `PATCH /api/v1/user` (aman: `PATCH /api/v2/user`) · toggle `api.API-A3-a`
- **Objective:** Set properti yang seharusnya tak boleh diubah user (role/balance/verified).
- **Hint 1:** Field apa yang dikembalikan objek user?
- **Hint 2:** Coba kirim field tambahan di body.
- **Hint 3:** Incar properti berhak-istimewa (mis. peran/saldo/verifikasi).

### API-A3-b · Excessive Data Exposure 🟢
- **Lokasi:** `GET /api/v1/users/{id}` (aman: `GET /api/v2/users/{id}`) · toggle `api.API-A3-b`
- **Objective:** Temukan data sensitif (password_hash/PII) yang ikut terkirim di respons.
- **Hint 1:** Baca respons JSON dengan teliti.
- **Hint 2:** Apakah ada field yang seharusnya internal?
- **Hint 3:** Bandingkan data-mu vs data user lain.

### API-A4 · Unrestricted Resource Consumption 🟢
- **Lokasi:** `GET /api/v1/products?limit=` (aman: `GET /api/v2/products`) · toggle `api.API-A4`
- **Objective:** Bebani/serobot data lewat parameter `limit` tanpa batas.
- **Hint 1:** Apakah `limit`/`page` dibatasi?
- **Hint 2:** Coba nilai yang sangat besar.
- **Hint 3:** Amati apakah tidak ada rate limit.

### API-A5 · Broken Function Level Authorization 🟡
- **Lokasi:** `POST /api/v1/admin/users/{id}/role` (aman: v2) · toggle `api.API-A5`
- **Objective:** Panggil fungsi admin sebagai user biasa.
- **Hint 1:** Endpoint admin ada di dokumentasi API?
- **Hint 2:** Coba panggil dengan token user biasa.
- **Hint 3:** Cek apakah pengecekan peran terpasang di endpoint itu.

### API-A6 · Unrestricted Access to Business Flows 🟡
- **Lokasi:** `POST /api/v1/promo/claim` · toggle `api.API-A6`
- **Objective:** Salahgunakan alur bisnis (klaim promo melebihi kuota per-user).
- **Hint 1:** Alur mana yang mengandaikan "pemakaian manusiawi"?
- **Hint 2:** Otomatisasi alur itu.
- **Hint 3:** Adakah pembatasan kecepatan/kuota?

### API-A7 · SSRF (API) 🟡
- **Lokasi:** `POST /api/v1/fetch-url` (aman: `POST /api/v2/fetch-url`) · toggle `api.API-A7`
- **Objective:** Buat server memanggil tujuan pilihanmu (internal lab).
- **Hint 1:** Endpoint mana yang menerima URL?
- **Hint 2:** Arahkan ke internal lab (mis. `internal-metadata`).
- **Hint 3:** Serupa Web-A10, tapi lewat API.

### API-A8 · Security Misconfiguration (API) 🟢
- **Lokasi:** `/docs` & `/openapi.json` (terbuka) + `GET /api/v1/server-info` · toggle `api.API-A8`
- **Objective:** Manfaatkan konfigurasi API yang terlalu terbuka (info server bocor).
- **Hint 1:** Apakah dokumentasi API terbuka publik?
- **Hint 2:** Endpoint apa yang terungkap dari sana?
- **Hint 3:** Coba method HTTP yang tak diharapkan.

### API-A9 · Improper Inventory Management 🟡
- **Lokasi:** `/api/v1` (lawas) vs `/api/v2`; endpoint undocumented `GET /api/v1/_debug/orders` · toggle `api.API-A9`
- **Objective:** Temukan versi/endpoint lama yang lebih rentan & tak terdokumentasi.
- **Hint 1:** Ada lebih dari satu versi API?
- **Hint 2:** Bandingkan perilaku v1 vs v2 untuk aksi yang sama.
- **Hint 3:** Cari endpoint yang tak terdokumentasi.

### API-A10 · Unsafe Consumption of 3rd-party API 🔴
- **Lokasi:** `POST /api/v1/orders/{id}/pay` (percaya `gateway_response` dari klien) · toggle `api.API-A10`
- **Objective:** Manfaatkan kepercayaan buta terhadap respons pihak ketiga (tandai order lunas tanpa bayar).
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

Status: ✅ aktif (implemented + enabled). Semua challenge Web & API kini aktif.

### Web — OWASP Top 10 (2021)
| Challenge | Kategori OWASP | Tool relevan | Status |
|---|---|---|---|
| Web-A01-a IDOR order/invoice | A01 Broken Access Control | Burp, DevTools | ✅ |
| Web-A01-b Forced admin | A01 Broken Access Control | Burp, ffuf | ✅ |
| Web-A01-c Product mutation | A01 Broken Access Control | Burp, curl | ✅ |
| Web-A02-a Weak md5 hash | A02 Cryptographic Failures | hashcat, john | ✅ |
| Web-A02-b Plaintext PII | A02 Cryptographic Failures | Burp (chain IDOR/SQLi) | ✅ |
| Web-A03-a SQL Injection | A03 Injection | sqlmap, Burp | ✅ |
| Web-A03-b XSS (stored/reflected) | A03 Injection | Browser, Burp | ✅ |
| Web-A03-c SSTI (Jinja2) | A03 Injection | tplmap, Burp | ✅ |
| Web-A03-d Command Injection | A03 Injection | commix, Burp | ✅ |
| Web-A04-a Qty negatif | A04 Insecure Design | Burp, curl | ✅ |
| Web-A04-b Race kupon (TOCTOU) | A04 Insecure Design | Burp Turbo Intruder | ✅ |
| Web-A05-a Verbose error/debug | A05 Security Misconfiguration | Browser, Burp | ✅ |
| Web-A05-b File & path ter-expose | A05 Security Misconfiguration | ffuf, dirsearch | ✅ |
| Web-A05-c CORS longgar | A05 Security Misconfiguration | Burp, PoC HTML | ✅ |
| Web-A06 Komponen ber-CVE | A06 Vulnerable Components | pip-audit, OSV, safety | ✅ |
| Web-A07-a Brute force | A07 Auth Failures | Hydra, Burp Intruder | ✅ |
| Web-A07-b Predictable token | A07 Auth Failures | Script kustom, Burp | ✅ |
| Web-A08 Insecure deserialization | A08 Integrity Failures | Burp, payload YAML | ✅ |
| Web-A09 Logging & monitoring | A09 Logging Failures | Observasi log | ✅ |
| Web-A10 SSRF via import URL | A10 SSRF | Burp, curl | ✅ |

### API — OWASP API Security Top 10 (2023)
| Challenge | Kategori OWASP API | Tool relevan | Status |
|---|---|---|---|
| API-A1 BOLA | API1 BOLA | Burp, Postman/httpie | ✅ |
| API-A2 Broken Auth (JWT) | API2 Broken Authentication | jwt_tool | ✅ |
| API-A3-a Mass Assignment | API3 Broken Object Property Level Auth | Burp, Postman | ✅ |
| API-A3-b Excessive Data Exposure | API3 Broken Object Property Level Auth | Burp, httpie | ✅ |
| API-A4 Unrestricted Resource Consumption | API4 | Burp, curl | ✅ |
| API-A5 Broken Function Level Auth | API5 | Postman, Burp | ✅ |
| API-A6 Business Flow Abuse | API6 | Script kustom | ✅ |
| API-A7 SSRF (API) | API7 | Burp, curl | ✅ |
| API-A8 Security Misconfiguration | API8 | Browser (`/docs`), Burp | ✅ |
| API-A9 Improper Inventory Mgmt | API9 | ffuf, banding v1/v2 | ✅ |
| API-A10 Unsafe 3rd-party Consumption | API10 | Burp, payment-mock | ✅ |
