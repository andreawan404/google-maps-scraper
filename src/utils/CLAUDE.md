# src/utils/ — Cross-Cutting Utilities

## Tanggung Jawab
Module ini dipakai oleh semua module lain. **Tidak boleh import dari `src/scraper/`, `src/enrichment/`, atau `src/storage/`.**

---

## File: logger.py

### Setup Loguru

```python
import sys
from loguru import logger
from config.settings import settings

def setup_logger():
    logger.remove()  # Hapus default handler

    # Console: warna + level sesuai settings
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
        colorize=True,
    )

    # File: rotasi harian, simpan 7 hari
    if settings.log_file:
        logger.add(
            settings.log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} — {message}",
            rotation="00:00",      # Rotasi tengah malam
            retention="7 days",
            compression="zip",
            encoding="utf-8",
        )

setup_logger()

# Export `logger` — semua module import ini
__all__ = ["logger"]
```

### Penggunaan

```python
from src.utils.logger import logger

logger.info("Mulai scraping: keyword={}, lokasi={}", keyword, location)
logger.debug("Extracted: {}", business.name)
logger.warning("Timeout untuk URL: {}", url)
logger.error("DB error saat upsert {}: {}", place_id, e)
```

**Jangan** gunakan `print()` atau `logging.getLogger()` di mana pun dalam project.

---

## File: rate_limiter.py

### Interface

```python
import asyncio
import random
from config.settings import settings

class RateLimiter:
    """Throttle requests untuk menghindari block dari Google."""

    async def wait(self) -> None:
        """Tunggu random delay antara min dan max dari settings."""
        delay = random.uniform(settings.min_delay_seconds, settings.max_delay_seconds)
        await asyncio.sleep(delay)

    async def wait_short(self) -> None:
        """Delay pendek untuk operasi intra-page (scroll, hover)."""
        await asyncio.sleep(random.uniform(0.3, 0.8))

    async def wait_long(self) -> None:
        """Delay panjang setelah error atau sebelum retry."""
        await asyncio.sleep(random.uniform(5.0, 10.0))

# Singleton
rate_limiter = RateLimiter()
```

### Penggunaan

```python
from src.utils.rate_limiter import rate_limiter

# Antara klik listing
await rate_limiter.wait()

# Antara scroll
await rate_limiter.wait_short()

# Setelah dapat error / timeout
await rate_limiter.wait_long()
```

---

## File: proxy_manager.py

### Interface

```python
from config.settings import settings
from typing import Optional
import itertools

class ProxyManager:
    """Round-robin rotation dari daftar proxy di settings."""

    def __init__(self):
        raw = settings.proxy_list
        self._proxies = [p.strip() for p in raw.split(",") if p.strip()] if raw else []
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None

    async def next_proxy(self) -> Optional[str]:
        """Return proxy berikutnya, atau None jika tidak ada proxy."""
        if not self._cycle:
            return None
        return next(self._cycle)

    def has_proxies(self) -> bool:
        return bool(self._proxies)

# Singleton
proxy_manager = ProxyManager()
```

### Format Proxy di .env

```
# Satu proxy
PROXY_LIST=http://user:pass@host:port

# Multiple proxy (round-robin)
PROXY_LIST=http://user:pass@proxy1:8080,http://user:pass@proxy2:8080
```

### Konversi ke Playwright Format

```python
def to_playwright_proxy(proxy_url: str) -> dict:
    """Konversi URL string ke dict format Playwright."""
    from urllib.parse import urlparse
    parsed = urlparse(proxy_url)
    result = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        result["username"] = parsed.username
        result["password"] = parsed.password or ""
    return result
```
