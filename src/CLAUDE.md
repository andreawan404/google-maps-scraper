# src/ — Source Code Utama

## Struktur Module

```
src/
├── scraper/       ← Browser automation & data extraction dari Google Maps
├── enrichment/    ← Post-processing: email finder + phone normalizer
├── storage/       ← Database ORM, repository pattern, CSV export
└── utils/         ← Cross-cutting concerns: logger, proxy, rate limiter
```

---

## Dependency Graph (tidak boleh dibalik arahnya)

```
scripts/main.py
    ↓
src/scraper/        src/enrichment/
    ↓                   ↓
src/storage/  ←─────────┘
    ↓
src/utils/
    ↓
config/settings.py
```

- `utils/` tidak boleh import dari `scraper/`, `enrichment/`, atau `storage/`
- `storage/` tidak boleh import dari `scraper/` atau `enrichment/`
- `config/settings.py` tidak boleh import dari `src/` apapun

---

## Konvensi Wajib di Seluruh src/

### Async
```python
# BENAR — semua I/O pakai async
async def fetch_data(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# SALAH — blocking di async context
def fetch_data(url: str) -> str:
    return requests.get(url).text  # JANGAN INI
```

### Type Hints
```python
# BENAR
async def extract_phone(page: Page) -> Optional[str]:

# SALAH
async def extract_phone(page):
```

### Error Handling
```python
# BENAR — log dan lanjut
try:
    result = await risky_operation()
except Exception as e:
    logger.warning("Failed to do X for {}: {}", identifier, e)
    result = None

# SALAH — biarkan crash
result = await risky_operation()
```

### Retry Pattern
```python
# Gunakan tenacity untuk semua network call
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_with_retry():
    ...
```

### Import Logger
```python
# Selalu gunakan ini — bukan logging stdlib, bukan print
from src.utils.logger import logger
```

---

## Package Initialization

Setiap subfolder wajib punya `__init__.py` (boleh kosong) agar bisa di-import sebagai package.
