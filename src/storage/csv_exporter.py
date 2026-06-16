from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from src.storage.models import Business, get_engine
from src.utils.logger import logger

# Urutan kolom CSV — sesuai dengan skema di CLAUDE.md root
EXPORT_COLUMNS = [
    "place_id",
    "name",
    "category",
    "address",
    "city",
    "province",
    "latitude",
    "longitude",
    "phone",
    "phone_normalized",
    "email",
    "website",
    "rating",
    "review_count",
    "maps_url",
    "scraped_at",
]


def export_to_csv(
    output_path: Optional[str] = None,
    only_with_contact: bool = False,
) -> int:
    """
    Export semua data dari SQLite ke CSV.
    Return: jumlah baris yang diekspor.
    Encoding utf-8-sig agar Excel Windows tidak corrupt karakter Indonesia.
    """
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

    rows = [{col: getattr(r, col, None) for col in EXPORT_COLUMNS} for r in records]
    df = pd.DataFrame(rows, columns=EXPORT_COLUMNS)

    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/result_{ts}.csv"

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info("Exported {} records → {}", len(df), output_path)
    return len(df)
