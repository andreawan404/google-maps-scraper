"""
Data Access Layer — semua operasi CRUD ke database.
Tidak ada SQL mentah di luar file ini.
"""
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.scraper.extractor import BusinessRaw
from src.storage.models import Business, get_engine
from src.utils.logger import logger


class BusinessRepository:
    """
    Interface tunggal untuk semua operasi database.
    Auto-connect ke SQLite via settings.DATABASE_URL.
    """

    def __init__(self):
        self.engine = get_engine()

    # ─────────────────────────────────────────────────────────────────────
    # WRITE OPERATIONS
    # ─────────────────────────────────────────────────────────────────────

    def upsert(self, business: BusinessRaw) -> None:
        """
        Insert atau update record bisnis.
        Idempotent: aman dipanggil berkali-kali dengan data yang sama.
        """
        city, province = _parse_city_province(business.address)

        data = {
            "place_id": business.place_id,
            "name": business.name,
            "category": business.category,
            "address": business.address,
            "city": city,
            "province": province,
            "latitude": business.latitude,
            "longitude": business.longitude,
            "phone": business.phone,
            "website": business.website,
            "rating": business.rating,
            "review_count": business.review_count,
            "maps_url": business.maps_url,
            "scraped_at": business.scraped_at,
            "enriched": False,
        }

        with Session(self.engine) as session:
            stmt = sqlite_insert(Business).values(**data)
            # Jika place_id sudah ada, update field yang mungkin berubah
            stmt = stmt.on_conflict_do_update(
                index_elements=["place_id"],
                set_={
                    "name": stmt.excluded.name,
                    "category": stmt.excluded.category,
                    "address": stmt.excluded.address,
                    "city": stmt.excluded.city,
                    "province": stmt.excluded.province,
                    "latitude": stmt.excluded.latitude,
                    "longitude": stmt.excluded.longitude,
                    "phone": stmt.excluded.phone,
                    "website": stmt.excluded.website,
                    "rating": stmt.excluded.rating,
                    "review_count": stmt.excluded.review_count,
                    "maps_url": stmt.excluded.maps_url,
                }
            )
            session.execute(stmt)
            session.commit()

    def update_email(self, place_id: str, email: Optional[str]) -> None:
        """Update field email setelah enrichment."""
        with Session(self.engine) as session:
            record = session.get(Business, place_id)
            if record:
                record.email = email
                record.email_checked_at = datetime.now(timezone.utc)
                session.commit()

    def update_phone_normalized(self, place_id: str, phone_normalized: Optional[str]) -> None:
        """Update field phone_normalized setelah normalisasi."""
        with Session(self.engine) as session:
            record = session.get(Business, place_id)
            if record:
                record.phone_normalized = phone_normalized
                session.commit()

    def mark_enriched(self, place_id: str) -> None:
        """Tandai record sebagai sudah di-enrich."""
        with Session(self.engine) as session:
            record = session.get(Business, place_id)
            if record:
                record.enriched = True
                session.commit()

    # ─────────────────────────────────────────────────────────────────────
    # READ OPERATIONS
    # ─────────────────────────────────────────────────────────────────────

    def get_all(self) -> list[Business]:
        """Ambil semua record."""
        with Session(self.engine) as session:
            return session.query(Business).all()

    def get_without_email(self) -> list[dict]:
        """
        Ambil bisnis yang belum dicek emailnya dan punya website.
        Return sebagai list of dict (lebih aman untuk async context).
        """
        with Session(self.engine) as session:
            records = (
                session.query(Business)
                .filter(
                    Business.email_checked_at.is_(None),
                    Business.website.isnot(None),
                )
                .all()
            )
            return [
                {"place_id": r.place_id, "name": r.name, "website": r.website}
                for r in records
            ]

    def get_without_normalized_phone(self) -> list[dict]:
        """Ambil bisnis yang phonenya belum dinormalisasi."""
        with Session(self.engine) as session:
            records = (
                session.query(Business)
                .filter(
                    Business.phone_normalized.is_(None),
                    Business.phone.isnot(None),
                )
                .all()
            )
            return [
                {"place_id": r.place_id, "phone": r.phone}
                for r in records
            ]

    def get_stats(self) -> dict:
        """Stats ringkas untuk CLI progress display."""
        with Session(self.engine) as session:
            total = session.query(Business).count()
            with_email = session.query(Business).filter(Business.email.isnot(None)).count()
            with_phone = session.query(Business).filter(Business.phone.isnot(None)).count()
            with_website = session.query(Business).filter(Business.website.isnot(None)).count()
            email_checked = session.query(Business).filter(Business.email_checked_at.isnot(None)).count()

            return {
                "total": total,
                "with_email": with_email,
                "with_phone": with_phone,
                "with_website": with_website,
                "email_checked": email_checked,
                "email_coverage": f"{(with_email / total * 100):.1f}%" if total > 0 else "0%",
                "phone_coverage": f"{(with_phone / total * 100):.1f}%" if total > 0 else "0%",
            }

    def exists(self, place_id: str) -> bool:
        """Cek apakah place_id sudah ada di DB."""
        with Session(self.engine) as session:
            return session.get(Business, place_id) is not None


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Parse city & province dari address string Indonesia
# ─────────────────────────────────────────────────────────────────────────────

_CITY_PATTERNS = [
    r'Kota\s+([A-Za-z\s]+?)(?:,|\d{5}|$)',
    r'Kab(?:upaten)?\.?\s+([A-Za-z\s]+?)(?:,|\d{5}|$)',
]

_PROVINCE_MAP = {
    "DKI Jakarta": "DKI Jakarta",
    "Jawa Barat": "Jawa Barat",
    "Jawa Tengah": "Jawa Tengah",
    "Jawa Timur": "Jawa Timur",
    "Banten": "Banten",
    "Sumatera Utara": "Sumatera Utara",
    "Sumatera Selatan": "Sumatera Selatan",
    "Kalimantan Timur": "Kalimantan Timur",
    "Sulawesi Selatan": "Sulawesi Selatan",
    "Bali": "Bali",
    # Tambah sesuai kebutuhan
}


def _parse_city_province(address: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Parse city dan province dari format address Indonesia."""
    if not address:
        return None, None

    city = None
    province = None

    for pattern in _CITY_PATTERNS:
        match = re.search(pattern, address, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            break

    for prov_name in _PROVINCE_MAP:
        if prov_name.lower() in address.lower():
            province = prov_name
            break

    return city, province
