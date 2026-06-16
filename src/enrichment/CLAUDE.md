# src/enrichment/ — Enrichment Pipeline

## Tanggung Jawab
Berjalan **setelah** semua data Maps selesai di-scrape. Dua tugas independen:
1. `email_finder.py` — Kunjungi website bisnis, cari email
2. `phone_normalizer.py` — Normalisasi nomor HP ke format Indonesia (+62)

---

## File: email_finder.py

### Interface Utama

```python
async def find_emails_for_businesses(
    businesses: list[dict],  # [{"place_id": ..., "name": ..., "website": ...}]
) -> dict[str, Optional[str]]:
    """
    Return: {place_id: email_or_None}
    Satu email terbaik per bisnis (prioritas: domain match > generic).
    """

async def find_email_from_url(url: str) -> Optional[str]:
    """
    Kunjungi URL → parse HTML → cari email.
    Cek halaman utama + /contact, /kontak, /about.
    """
```

### Strategi Pencarian Email

1. **mailto: links**: `soup.select('a[href^="mailto:"]')` → paling reliable
2. **Regex pada teks**: `r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'`
3. **Halaman kontak**: jika tidak ketemu di homepage, coba `/contact`, `/kontak`, `/hubungi-kami`

### Prioritas Email
```python
def _rank_email(email: str, domain: str) -> int:
    """Skor lebih tinggi = lebih diutamakan."""
    score = 0
    local = email.split("@")[0].lower()
    if domain and domain in email:
        score += 10   # Email domain match website
    if local in ("info", "contact", "hello", "halo", "admin", "cs"):
        score += 5    # Generic business email
    if local.startswith("no-reply") or local.startswith("noreply"):
        score -= 20   # Blacklist
    return score
```

### Blacklist Email
Jangan return email yang mengandung: `noreply`, `no-reply`, `example.com`, `sentry.io`, `@2x`, `.png`, `.jpg`

### HTTP Client Settings
```python
# Pakai httpx async, bukan requests
async with httpx.AsyncClient(
    timeout=settings.email_timeout_seconds,
    follow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0 ..."},  # User agent realistis
    verify=False,  # Banyak UMKM pakai cert expired
) as client:
    ...
```

### Concurrency
- Jalankan max **5 concurrent** requests (asyncio.Semaphore(5))
- Jangan blast semua website sekaligus — rate limiter tetap berlaku
- Total timeout per bisnis: 15 detik (termasuk halaman kontak)

---

## File: phone_normalizer.py

### Interface Utama

```python
def normalize_phones_batch(
    records: list[dict],  # [{"place_id": ..., "phone": ...}]
) -> dict[str, Optional[str]]:
    """Return: {place_id: normalized_phone_or_None}"""

def normalize_phone(raw: str, country: str = "ID") -> Optional[str]:
    """
    Normalisasi satu nomor ke format E.164 (+62xxx).
    Return None jika tidak valid.
    """
```

### Logic Normalisasi

```python
import phonenumbers

def normalize_phone(raw: str, country: str = "ID") -> Optional[str]:
    if not raw:
        return None
    try:
        # Bersihkan dulu
        cleaned = re.sub(r'[^\d+]', '', raw)

        # Handle format lokal Indonesia
        if cleaned.startswith("08"):
            cleaned = "+62" + cleaned[1:]
        elif cleaned.startswith("8") and len(cleaned) >= 9:
            cleaned = "+62" + cleaned
        elif cleaned.startswith("628"):
            cleaned = "+" + cleaned

        parsed = phonenumbers.parse(cleaned, country)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return None
```

### Kasus Edge
- `021-5551234` → `+62215551234` (Jakarta landline)
- `+62 21 555 1234` → `+62215551234`
- `08xx-xxxx-xxxx` → `+628xxxxxxxxx`
- `(031) 123456` → `+62311234565`
- `0800-xxx-xxx` (toll-free) → tetap simpan apa adanya, bukan dinormalisasi
