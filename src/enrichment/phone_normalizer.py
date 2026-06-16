import re
from typing import Optional

import phonenumbers
from phonenumbers import PhoneNumberFormat, NumberParseException

from src.utils.logger import logger


def normalize_phones_batch(
    records: list[dict],
) -> dict[str, Optional[str]]:
    """
    Normalisasi batch phone numbers.
    Input: [{"place_id": ..., "phone": ...}]
    Return: {place_id: normalized_e164_or_None}
    """
    return {r["place_id"]: normalize_phone(r.get("phone")) for r in records}


def normalize_phone(raw: Optional[str], country: str = "ID") -> Optional[str]:
    """
    Normalisasi satu nomor ke format E.164 (+62xxx).
    Menangani format lokal Indonesia: 08xx, 628x, (021), +62 21, dll.
    Return None jika nomor tidak valid.
    """
    if not raw:
        return None

    try:
        # Bersihkan semua karakter non-digit kecuali +
        cleaned = re.sub(r'[^\d+]', '', raw)

        if not cleaned:
            return None

        # Normalisasi prefix lokal Indonesia ke format E.164
        if cleaned.startswith("08"):
            cleaned = "+62" + cleaned[1:]
        elif cleaned.startswith("628"):
            cleaned = "+" + cleaned
        elif cleaned.startswith("62") and len(cleaned) >= 10:
            # "62 21 555 1234" → "62215551234" → "+62215551234"
            cleaned = "+" + cleaned
        elif re.match(r'^8\d{8,11}$', cleaned):
            # Nomor HP tanpa prefix (mis: 81234567890)
            cleaned = "+62" + cleaned
        elif re.match(r'^02\d', cleaned) or re.match(r'^03\d', cleaned):
            # Nomor telepon rumah/kantor Indonesia (mis: 021xxxx, 031xxxx)
            cleaned = "+62" + cleaned[1:]

        parsed = phonenumbers.parse(cleaned, country)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)

    except NumberParseException:
        logger.debug("Tidak bisa parse nomor: '{}'", raw)
    except Exception as e:
        logger.debug("Error normalize_phone '{}': {}", raw, e)

    return None
