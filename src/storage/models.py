from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine as _create_engine

from sqlalchemy import Engine

_engine: Engine | None = None


class Base(DeclarativeBase):
    pass


class Business(Base):
    __tablename__ = "businesses"

    # Primary key — Google Maps Place ID
    place_id = Column(String, primary_key=True)

    # Data inti dari Maps
    name = Column(String, nullable=False)
    category = Column(String)
    address = Column(Text)
    city = Column(String)
    province = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    phone = Column(String)
    website = Column(String)
    rating = Column(Float)
    review_count = Column(Integer)
    maps_url = Column(String)
    scraped_at = Column(DateTime)

    # Enrichment (diisi setelah pipeline enrichment)
    email = Column(String)
    phone_normalized = Column(String)   # Format E.164: +62xxx
    email_checked_at = Column(DateTime) # None = belum pernah dicek
    enriched = Column(Boolean, default=False)


def get_engine() -> Engine:
    """Singleton engine. Auto-create semua tabel jika belum ada."""
    global _engine
    if _engine is None:
        from config.settings import settings
        _engine = _create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(_engine)
    return _engine
