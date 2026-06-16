# tests/ — Testing Guide

## Filosofi Testing
- **Unit test**: untuk pure functions (parser, normalizer, helper)
- **Integrasi test**: untuk DB layer (pakai SQLite in-memory)
- **JANGAN** mock Playwright atau httpx di unit tests — gunakan fixtures dengan data statis
- **JANGAN** test terhadap Google Maps live (rate-limited, flaky, ToS)

---

## File: conftest.py

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.storage.models import Base, Business

@pytest.fixture
def in_memory_engine():
    """SQLite in-memory untuk tests — fresh setiap test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def sample_business_raw():
    """BusinessRaw fixture untuk tests."""
    from src.scraper.extractor import BusinessRaw
    return BusinessRaw(
        place_id="ChIJtest123",
        name="Apotek Sehat",
        category="Apotek",
        address="Jl. Sudirman No.1, Kota Bandung, Jawa Barat",
        phone="022-1234567",
        website="https://apoteksehat.co.id",
        rating=4.5,
        review_count=127,
        latitude=-6.914744,
        longitude=107.608960,
        maps_url="https://maps.google.com/?q=apotek+sehat",
    )

@pytest.fixture
def repo(in_memory_engine):
    """BusinessRepository dengan DB in-memory."""
    from src.storage.repository import BusinessRepository
    r = BusinessRepository()
    r.engine = in_memory_engine  # Override engine
    return r
```

---

## File: test_extractor.py

Test untuk helper functions di `extractor.py`:

```python
from src.scraper.extractor import (
    _extract_place_id,
    _extract_coords_from_url,
    _clean_phone,
    _parse_float,
    _parse_review_count,
)

def test_extract_place_id_from_data_param():
    url = "https://www.google.com/maps/place/Apotek/@-6.9147,107.6089,17z/data=!4m6!3m5!1sChIJtest123"
    assert _extract_place_id(url) == "ChIJtest123"

def test_extract_coords():
    url = "https://www.google.com/maps/place/test/@-6.9147,107.6089,17z"
    lat, lng = _extract_coords_from_url(url)
    assert abs(lat - (-6.9147)) < 0.001
    assert abs(lng - 107.6089) < 0.001

def test_clean_phone_prefix():
    assert _clean_phone("Phone: +62 21 555 1234") == "+62 21 555 1234"
    assert _clean_phone("Telepon: 022-1234") == "022-1234"
    assert _clean_phone(None) is None

def test_parse_review_count_with_separator():
    assert _parse_review_count("1.234 ulasan") == 1234
    assert _parse_review_count("50") == 50
    assert _parse_review_count(None) is None
```

---

## File: test_phone_normalizer.py

```python
from src.enrichment.phone_normalizer import normalize_phone

@pytest.mark.parametrize("raw,expected", [
    ("08123456789", "+628123456789"),
    ("+62 21 555 1234", "+62215551234"),
    ("021-5551234", "+62215551234"),
    ("(031) 1234567", "+62311234567"),
    ("invalid", None),
    ("", None),
    (None, None),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected
```

---

## File: test_repository.py

```python
def test_upsert_and_exists(repo, sample_business_raw):
    assert not repo.exists(sample_business_raw.place_id)
    repo.upsert(sample_business_raw)
    assert repo.exists(sample_business_raw.place_id)

def test_upsert_is_idempotent(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    repo.upsert(sample_business_raw)  # Tidak boleh error
    stats = repo.get_stats()
    assert stats["total"] == 1

def test_update_email(repo, sample_business_raw):
    repo.upsert(sample_business_raw)
    repo.update_email(sample_business_raw.place_id, "info@apoteksehat.co.id")
    pending = repo.get_without_email()
    assert len(pending) == 0  # Sudah punya email
```

---

## Cara Jalankan Tests

```bash
# Semua tests
pytest tests/ -v

# Hanya extractor
pytest tests/test_extractor.py -v

# Dengan coverage
pytest tests/ --cov=src --cov-report=term-missing
```

## Yang TIDAK Perlu Ditest
- Playwright browser behavior (test dengan real browser → lambat, flaky)
- Koneksi ke Google Maps live
- CSV encoding (pandas sudah teruji)
