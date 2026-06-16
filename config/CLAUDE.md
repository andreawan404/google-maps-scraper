# config/ — Konfigurasi Terpusat

## Tujuan
Satu-satunya sumber kebenaran untuk semua nilai konfigurasi. **Tidak ada nilai hardcode di luar folder ini.**

---

## File: settings.py

Gunakan `pydantic-settings` (`BaseSettings`) agar env vars otomatis terbaca dari `.env`.

### Struktur Class

```python
from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

class Settings(BaseSettings):
    # Browser
    headless: bool = Field(True, env="HEADLESS")
    browser_timeout: int = Field(30000, env="BROWSER_TIMEOUT")

    # Rate limiting
    min_delay_seconds: float = Field(2.0, env="MIN_DELAY_SECONDS")
    max_delay_seconds: float = Field(5.0, env="MAX_DELAY_SECONDS")

    # Database
    database_url: str = Field("sqlite:///output/scraper.db", env="DATABASE_URL")

    # Proxy
    proxy_list: str = Field("", env="PROXY_LIST")  # comma-separated

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("output/scraper.log", env="LOG_FILE")

    # Email finder
    email_timeout_seconds: int = Field(10, env="EMAIL_TIMEOUT_SECONDS")
    max_email_per_site: int = Field(3, env="MAX_EMAIL_PER_SITE")

    # Retry
    max_retries: int = Field(3, env="MAX_RETRIES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### Aturan Wajib

- **Singleton**: selalu import `settings` (bukan `Settings()`), kecuali di tests
- **Derived paths**: konversi `database_url` ke path absolut jika diperlukan SQLAlchemy
- **Validasi**: tambahkan `@validator` untuk nilai yang punya constraint (misal: delay > 0)
- **Proxy parsing**: `settings.proxy_list.split(",")` untuk dapat list proxy

---

## Yang TIDAK Boleh Ada di Sini

- Logic bisnis apapun
- Import dari `src/` (ini akan membuat circular import)
- Nilai default yang tidak masuk akal untuk production
