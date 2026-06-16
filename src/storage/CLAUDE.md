# src/storage/ — Storage Layer

## Tanggung Jawab
1. `models.py` — SQLAlchemy ORM models + engine factory
2. `repository.py` — Semua operasi database (CRUD, deduplication, stats)
3. `csv_exporter.py` — Export SQLite → pandas DataFrame → CSV

---

## File: models.py

### Schema Lengkap

```python
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine

class Base(DeclarativeBase):
    pass

class Business(Base):
    __tablename__ = "businesses"

    # Primary key
    place_id = Column(String, primary_key=True)

    # Core data dari Maps
    name = Column(String, nullable=False)
    category = Column(String)
    address = Column(Text)
    city = Column(String)           # Parsed dari address
    province = Column(String)       # Parsed dari address
    latitude = Column(Float)
    longitude = Column(Float)
    phone = Column(String)          # Raw dari Maps
    website = Column(String)
    rating = Column(Float)
    review_count = Column(Integer)
    maps_url = Column(String)
    scraped_at = Column(DateTime)

    # Enrichment fields (diisi setelah enrichment)
    email = Column(String)
    phone_normalized = Column(String)  # Format E.164 (+62xxx)
    email_checked_at = Column(DateTime)
    enriched = Column(Boolean, default=False)

def get_engine():
    """Singleton engine. Auto-create tables jika belum ada."""
    from config.settings import settings
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    return engine
```

### Aturan Model
- `place_id` adalah PRIMARY KEY — unik, tidak auto-increment
- `email_checked_at` = None berarti belum pernah dicek (bukan berarti tidak ada email)
- `enriched` = True berarti KEDUA email + phone sudah diproses
- Jangan tambah kolom baru tanpa update `csv_exporter.py` juga

---

## File: repository.py

File ini **sudah ada** di root project (`repository.py`) — **pindahkan ke sini tanpa modifikasi**.

### Method Inventory

| Method | Fungsi |
|--------|--------|
| `upsert(business)` | Insert atau update by place_id |
| `update_email(place_id, email)` | Set email + email_checked_at |
| `update_phone_normalized(place_id, phone)` | Set phone_normalized |
| `mark_enriched(place_id)` | Set enriched=True |
| `get_all()` | Semua records |
| `get_without_email()` | Records dengan website tapi belum dicek emailnya |
| `get_without_normalized_phone()` | Records dengan phone tapi belum dinormalisasi |
| `get_stats()` | Dict statistik untuk CLI |
| `exists(place_id)` | Boolean cek duplikat |

### Aturan Repository
- **Tidak ada SQL mentah** — semua lewat SQLAlchemy ORM atau `insert().on_conflict_do_update()`
- Setiap method buka dan tutup `Session` sendiri (tidak share session antar method)
- `get_without_email()` dan `get_without_normalized_phone()` return `list[dict]` bukan ORM objects — aman untuk asyncio context

---

## File: csv_exporter.py

### Interface Utama

```python
def export_to_csv(
    output_path: Optional[str] = None,
    only_with_contact: bool = False,
) -> int:
    """
    Export semua data dari DB ke CSV.
    Return: jumlah rows yang diekspor.
    Auto-generate filename: output/result_YYYYMMDD_HHMMSS.csv
    """
```

### Kolom Output CSV (urutan penting untuk readability)

```python
EXPORT_COLUMNS = [
    "place_id", "name", "category",
    "address", "city", "province",
    "latitude", "longitude",
    "phone", "phone_normalized", "email",
    "website", "rating", "review_count",
    "maps_url", "scraped_at",
]
```

### Logic Export

```python
def export_to_csv(output_path=None, only_with_contact=False):
    from src.storage.models import Business, get_engine
    import pandas as pd
    from datetime import datetime

    engine = get_engine()
    with Session(engine) as session:
        query = session.query(Business)
        if only_with_contact:
            query = query.filter(
                (Business.email.isnot(None)) | (Business.phone_normalized.isnot(None))
            )
        records = query.all()

    if not records:
        logger.warning("Tidak ada data untuk diekspor")
        return 0

    df = pd.DataFrame([{col: getattr(r, col, None) for col in EXPORT_COLUMNS} for r in records])

    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/result_{ts}.csv"

    df.to_csv(output_path, index=False, encoding="utf-8-sig")  # utf-8-sig untuk Excel compatibility
    logger.info("Exported {} records ke {}", len(df), output_path)
    return len(df)
```

**Penting**: gunakan `encoding="utf-8-sig"` bukan `utf-8` agar Excel Windows tidak corrupt karakter Indonesia.
