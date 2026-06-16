# src/scraper/ — Browser Automation & Extraction

## Tanggung Jawab
1. `browser.py` — Buat dan kelola Playwright browser instance (stealth mode)
2. `maps_scraper.py` — Navigasi Google Maps: search, scroll, yield URL per listing
3. `extractor.py` — Klik listing individual, ekstrak semua field ke `BusinessRaw`

---

## File: browser.py

### Yang Harus Ada

```python
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

async def create_browser(proxy: Optional[str] = None, headless: bool = True) -> Browser:
    """Factory untuk browser instance dengan stealth patch."""
    ...

async def create_context(browser: Browser) -> BrowserContext:
    """Context dengan user-agent realistis + viewport acak."""
    ...

async def new_stealth_page(context: BrowserContext) -> Page:
    """Page dengan stealth scripts diinjeksi (sembunyikan webdriver flags)."""
    ...
```

### Stealth Requirements
- Set `navigator.webdriver = undefined`
- Gunakan user-agent Chrome desktop terbaru (bukan headless)
- Random viewport: pilih dari preset umum (1366x768, 1920x1080, 1440x900)
- Disable `--blink-settings=imagesEnabled=false` KECUALI ada flag `--no-images`
- Proxy format: `{"server": "http://host:port", "username": "...", "password": "..."}`

### Context Manager Pattern
```python
@asynccontextmanager
async def browser_session(proxy=None):
    async with async_playwright() as p:
        browser = await create_browser(p, proxy)
        try:
            yield browser
        finally:
            await browser.close()
```

---

## File: maps_scraper.py

### Interface Utama

```python
class CaptchaError(Exception):
    """Raised jika Google menampilkan CAPTCHA challenge."""
    pass

async def scrape_google_maps(
    keyword: str,
    location: str,
    max_results: int = 100,
    proxy: Optional[str] = None,
) -> AsyncGenerator[BusinessRaw, None]:
    """
    Generator async — yield BusinessRaw satu per satu saat ditemukan.
    Caller bisa stop kapanpun (partial results tersimpan di DB).
    """
```

### Alur Scraping

1. Buka `https://www.google.com/maps/search/{keyword}+{location}`
2. Tunggu `SELECTORS["results_feed"]` muncul (timeout 15s)
3. Deteksi CAPTCHA: cek `iframe[src*="recaptcha"]` → raise `CaptchaError`
4. Loop scroll:
   - Ambil semua `SELECTORS["result_item"]` yang terlihat
   - Klik tiap item → tunggu detail panel load → `extract_business_from_page()`
   - Yield hasilnya
   - Scroll ke bawah (simulasi manusia: random delay dari `rate_limiter`)
   - Cek `SELECTORS["no_results"]` → break jika sudah habis
   - Break jika sudah `>= max_results`

### Anti-Detection Rules
- Jangan load lebih dari 1 page secara paralel
- Random delay antara klik: pakai `rate_limiter.wait()`
- Simulasikan mouse move sebelum klik: `page.mouse.move(x, y)` dulu
- Jangan langsung scroll penuh — gunakan `page.evaluate("window.scrollBy(0, 300)")`

---

## File: extractor.py

File ini **sudah ada** di root project (`extractor.py`) — **pindahkan ke sini tanpa modifikasi**.

### Aturan SELECTORS Dict
```python
SELECTORS = {
    # SEMUA selector dikumpulkan di sini
    # Jika Google update DOM → cukup update dict ini
    "name": "h1.DUwDvf",
    ...
}
```

**LARANGAN KERAS**: Jangan taruh selector CSS/XPath di luar dict `SELECTORS`. Jika ada selector baru, tambahkan dulu ke dict, baru gunakan dengan `SELECTORS["key"]`.

---

## Error Handling di Scraper

| Situasi | Penanganan |
|---------|-----------|
| Element tidak ditemukan | Return `None` (field optional) |
| `name` tidak ada | Raise `ExtractorError`, skip listing |
| Timeout navigasi | Log warning, retry 1x, lalu skip |
| CAPTCHA | Raise `CaptchaError` ke atas (propagate ke CLI) |
| Network error | Retry dengan exponential backoff (max 3x) |
