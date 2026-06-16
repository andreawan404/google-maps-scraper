# Google Maps Business Scraper

Scraper data bisnis dari Google Maps untuk kebutuhan **marketing & sales B2B**.
Output berupa file CSV dengan data kontak lengkap per bisnis.

> **Disclaimer:** Tool ini menggunakan browser automation untuk data bisnis yang
> dipublikasikan secara umum di Google Maps. Pastikan penggunaan sesuai regulasi
> yang berlaku (UU PDP Indonesia, GDPR jika relevan). Gunakan rate limiting yang
> wajar agar tidak membebani server.

---

## Fitur

- Scrape nama, kategori, alamat, koordinat, telepon, website, rating & jumlah ulasan
- Auto-cari email dari website bisnis (mailto links + regex)
- Normalisasi nomor HP ke format E.164 (+62xxx) untuk Indonesia
- Resume-able: data tersimpan di SQLite, scraping bisa dilanjut jika interrupt
- Deduplication otomatis berdasarkan Google Maps Place ID
- Anti-detection: random delay, stealth browser, rotasi proxy (opsional)

---

## Prasyarat

- Python 3.11+
- pip

---

## Instalasi

```bash
# 1. Clone repo
git clone https://github.com/aanandreawan/google-maps-scraper.git
cd google-maps-scraper

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Chromium untuk Playwright
python -m playwright install chromium

# 4. Buat file konfigurasi
cp .env.example .env
```

Edit `.env` jika ingin mengubah settings (headless mode, delay, proxy, dll).

---

## Cara Pakai

```bash
# Scrape 100 apotek di Bandung, langsung export ke CSV
python scripts/main.py scrape -k "apotek" -l "Bandung" -n 100 --export

# Scrape 200 distributor beras di Surabaya
python scripts/main.py scrape -k "distributor beras" -l "Surabaya" -n 200 --export

# Scrape dulu, export belakangan
python scripts/main.py scrape -k "klinik gigi" -l "Jakarta Selatan" -n 150
python scripts/main.py export -o output/klinik_jaksel.csv

# Export hanya data yang punya email atau telepon
python scripts/main.py export --with-contact-only -o output/punya_kontak.csv

# Jalankan enrichment manual (cari email + normalisasi phone)
python scripts/main.py enrich

# Lihat statistik database
python scripts/main.py stats
```

### Semua Options

```
scrape  --keyword / -k     Kata kunci pencarian          (wajib)
        --location / -l    Kota/lokasi                   (wajib)
        --max-results / -n Jumlah maksimum hasil         (default: 100)
        --export           Export CSV setelah selesai
        --no-enrich        Skip email enrichment
        --proxy            Proxy URL override
        --output / -o      Path file CSV output

export  --output / -o      Path file CSV output
        --with-contact-only  Hanya data yang punya kontak

enrich  --email-only       Hanya cari email
        --phone-only       Hanya normalisasi telepon
```

---

## Schema Output CSV

| Kolom | Deskripsi | Contoh |
|---|---|---|
| `place_id` | Google Maps Place ID (unique key) | ChIJxxxxxxxx |
| `name` | Nama bisnis | PT Maju Bersama |
| `category` | Kategori bisnis | Distributor |
| `address` | Alamat lengkap | Jl. Sudirman No.1, Jakarta |
| `city` | Kota | Jakarta Pusat |
| `province` | Provinsi | DKI Jakarta |
| `latitude` | Koordinat latitude | -6.208763 |
| `longitude` | Koordinat longitude | 106.845599 |
| `phone` | Telepon (raw dari Maps) | (021) 555-1234 |
| `phone_normalized` | Telepon format E.164 | +62215551234 |
| `email` | Email dari website bisnis | info@maju.co.id |
| `website` | URL website | https://maju.co.id |
| `rating` | Rating Google (1.0–5.0) | 4.5 |
| `review_count` | Jumlah ulasan | 127 |
| `maps_url` | Link Google Maps listing | https://maps.google.com/… |
| `scraped_at` | Timestamp scraping | 2026-06-16 10:30:00 |

---

## Konfigurasi (.env)

Salin `.env.example` ke `.env` lalu sesuaikan:

```env
HEADLESS=true               # false untuk lihat browser saat scraping
BROWSER_TIMEOUT=30000       # timeout browser (ms)
MIN_DELAY_SECONDS=2         # delay minimum antar request
MAX_DELAY_SECONDS=5         # delay maksimum antar request
DATABASE_URL=sqlite:///output/scraper.db
LOG_LEVEL=INFO
PROXY_LIST=                 # opsional: http://user:pass@host:port
```

---

## Struktur Project

```
google-maps-scraper/
├── config/         # Konfigurasi terpusat (pydantic-settings)
├── src/
│   ├── scraper/    # Playwright browser + Google Maps navigation
│   ├── enrichment/ # Email finder + phone normalizer
│   ├── storage/    # SQLAlchemy models + repository + CSV exporter
│   └── utils/      # Logger, rate limiter, proxy manager
├── scripts/        # CLI entry point (Click)
├── tests/          # Unit & integration tests
└── output/         # Hasil scraping (di-gitignore)
```

---

## Menjalankan Tests

```bash
pytest tests/ -v
```

---

## Tech Stack

| Layer | Library |
|---|---|
| Browser Automation | Playwright + stealth |
| HTTP Client | httpx (async) |
| HTML Parsing | BeautifulSoup4 + lxml |
| Phone Validation | phonenumbers |
| Database | SQLAlchemy + SQLite |
| Data Export | pandas |
| CLI | Click |
| Logging | loguru |
| Config | pydantic-settings |
