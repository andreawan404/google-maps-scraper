# Google Maps Business Scraper

## Tujuan Proyek
Scraper data bisnis dari Google Maps untuk kebutuhan **marketing & sales**.
Target output: file CSV dengan data kontak lengkap per bisnis.

> ⚠️ **Disclaimer**: Tool ini menggunakan browser automation. Pastikan
> penggunaan mematuhi regulasi data pribadi yang berlaku (UU PDP Indonesia,
> GDPR jika relevan). Data bisnis yang dipublikasikan secara umum di Google
> Maps umumnya dapat digunakan untuk kebutuhan B2B marketing.

---

## Tech Stack

| Layer           | Library / Tool             | Versi    |
|-----------------|----------------------------|----------|
| Browser Auto    | Playwright + stealth patch | 1.44+    |
| HTTP Client     | httpx (async)              | 0.27+    |
| HTML Parsing    | BeautifulSoup4 + lxml      | 4.12+    |
| Phone Validate  | phonenumbers               | 8.13+    |
| Storage         | SQLAlchemy + SQLite        | 2.0+     |
| Data Export     | pandas                     | 2.2+     |
| CLI             | Click                      | 8.1+     |
| Logging         | Loguru                     | 0.7+     |
| Config          | python-dotenv              | 1.0+     |

---

## Arsitektur Proyek

```
google-maps-scraper/
├── CLAUDE.md                  ← Kamu di sini
├── .env                       ← Runtime secrets (jangan di-commit)
├── .env.example               ← Template env vars
├── requirements.txt
├── pyproject.toml
│
├── config/
│   ├── CLAUDE.md              ← Panduan konfigurasi
│   └── settings.py            ← Semua config terpusat (via pydantic-settings)
│
├── src/
│   ├── CLAUDE.md              ← Panduan source code
│   ├── scraper/
│   │   ├── CLAUDE.md          ← Panduan scraper module
│   │   ├── browser.py         ← Playwright browser factory + stealth
│   │   ├── maps_scraper.py    ← Logika scraping Google Maps (search + scroll)
│   │   └── extractor.py       ← Ekstraksi field dari DOM element
│   ├── enrichment/
│   │   ├── CLAUDE.md          ← Panduan enrichment pipeline
│   │   ├── email_finder.py    ← Kunjungi website bisnis → cari email
│   │   └── phone_normalizer.py← Validasi & normalisasi nomor HP (ID format)
│   ├── storage/
│   │   ├── CLAUDE.md          ← Panduan storage layer
│   │   ├── models.py          ← SQLAlchemy ORM models
│   │   ├── repository.py      ← Data access layer (CRUD + deduplication)
│   │   └── csv_exporter.py    ← Export SQLite → CSV final
│   └── utils/
│       ├── CLAUDE.md          ← Panduan utilities
│       ├── proxy_manager.py   ← Rotasi proxy dari file/env
│       ├── rate_limiter.py    ← Throttle requests agar tidak ke-block
│       └── logger.py          ← Konfigurasi loguru + file log
│
├── scripts/
│   ├── CLAUDE.md              ← Panduan CLI commands
│   └── main.py                ← Entry point CLI (click commands)
│
├── output/                    ← CSV hasil scraping (di-gitignore)
│   └── .gitkeep
│
└── tests/
    ├── CLAUDE.md              ← Panduan testing
    ├── conftest.py
    └── test_extractor.py
```

---

## Data Flow

```
[User: keyword + lokasi]
        ↓
[maps_scraper.py] → Playwright buka Google Maps → Search → Scroll results
        ↓ list of URLs
[extractor.py] → Klik tiap listing → Extract: nama, alamat, phone, website,
                  rating, review_count, kategori, koordinat (dari URL)
        ↓ BusinessRaw objects
[repository.py] → Simpan ke SQLite (deduplication by place_id)
        ↓
[email_finder.py] → Untuk setiap bisnis yang punya website:
                    httpx GET → BeautifulSoup → cari mailto: & regex email
        ↓
[phone_normalizer.py] → Parse & normalisasi ke format +62xxx
        ↓
[csv_exporter.py] → pandas DataFrame → output/result_YYYYMMDD_HHMMSS.csv
```

---

## CSV Output Schema

| Kolom            | Deskripsi                              | Contoh                    |
|------------------|----------------------------------------|---------------------------|
| place_id         | Google Maps Place ID (unique key)      | ChIJxxxxxxxx              |
| name             | Nama bisnis                            | PT Maju Bersama           |
| category         | Kategori bisnis                        | Distributor               |
| address          | Alamat lengkap                         | Jl. Sudirman No.1, Jakarta|
| city             | Kota (parsed dari address)             | Jakarta Pusat             |
| province         | Provinsi                               | DKI Jakarta               |
| latitude         | Koordinat latitude                     | -6.208763                 |
| longitude        | Koordinat longitude                    | 106.845599                |
| phone            | Nomor HP/telp (normalized)             | +6221xxxxxxx              |
| email            | Email (dari website bisnis)            | info@majubersama.co.id    |
| website          | URL website                            | https://majubersama.co.id |
| rating           | Rating Google (1.0–5.0)               | 4.5                       |
| review_count     | Jumlah review                          | 127                       |
| maps_url         | Link Google Maps listing               | https://maps.google.com/…  |
| scraped_at       | Timestamp scraping                     | 2026-06-15 10:30:00       |

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Scrape keyword di kota tertentu
python scripts/main.py scrape \
  --keyword "distributor beras" \
  --location "Surabaya" \
  --max-results 500

# Export hasil ke CSV
python scripts/main.py export --output output/hasil.csv

# Scrape + langsung export
python scripts/main.py scrape \
  --keyword "apotek" \
  --location "Bandung" \
  --max-results 200 \
  --export

# Lihat progress / stats
python scripts/main.py stats
```

---

## Konvensi Kode

- **Async-first**: gunakan `async/await` untuk semua I/O (Playwright, httpx)
- **Type hints**: semua fungsi wajib pakai type hints
- **Dataclass**: gunakan `@dataclass` untuk data transfer objects
- **Error handling**: jangan biarkan exception tidak tertangani; log + continue
- **Retry**: semua network call wajib pakai retry logic (max 3x, exponential backoff)
- **Logging**: gunakan `from src.utils.logger import logger` (bukan `print`)
- **Config**: semua nilai configurable wajib lewat `config/settings.py`, bukan hardcode

---

## Environment Variables (.env)

```env
# Proxy (opsional - format: http://user:pass@host:port)
PROXY_LIST=proxy1.example.com:8080,proxy2.example.com:8080

# Browser settings
HEADLESS=true
BROWSER_TIMEOUT=30000

# Rate limiting
MIN_DELAY_SECONDS=2
MAX_DELAY_SECONDS=5

# Database
DATABASE_URL=sqlite:///output/scraper.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=output/scraper.log
```

---

## Penting untuk Claude Code

- Jika ada selector Google Maps yang berubah, update di `src/scraper/extractor.py`
  di bagian `SELECTORS` dict — **jangan** scatter selector ke seluruh codebase
- SQLite digunakan sebagai checkpoint: scraping bisa di-resume jika interrupt
- Setiap `place_id` hanya disimpan sekali (UNIQUE constraint di DB)
- Email enrichment berjalan **setelah** semua data Maps sudah di-scrape
- Output CSV final selalu di folder `output/` dengan timestamp di nama file
