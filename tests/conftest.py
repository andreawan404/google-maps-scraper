from datetime import datetime

import pytest
from sqlalchemy import create_engine

from src.scraper.extractor import BusinessRaw
from src.storage.models import Base, Business
from src.storage.repository import BusinessRepository


@pytest.fixture
def in_memory_engine():
    """SQLite in-memory — fresh setiap test, drop setelah selesai."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_business_raw() -> BusinessRaw:
    """BusinessRaw lengkap sebagai fixture standar antar test."""
    return BusinessRaw(
        place_id="ChIJtest123",
        name="Apotek Sehat",
        category="Apotek",
        address="Jl. Sudirman No.1, Kota Bandung, Jawa Barat 40111",
        phone="022-1234567",
        website="https://apoteksehat.co.id",
        rating=4.5,
        review_count=127,
        latitude=-6.914744,
        longitude=107.608960,
        maps_url="https://maps.google.com/?q=apotek+sehat",
        scraped_at=datetime(2026, 6, 16, 10, 0, 0),
    )


@pytest.fixture
def repo(in_memory_engine) -> BusinessRepository:
    """BusinessRepository dengan engine di-override ke in-memory SQLite."""
    r = BusinessRepository()
    r.engine = in_memory_engine
    return r
