import pytest

from src.enrichment.phone_normalizer import normalize_phone, normalize_phones_batch


@pytest.mark.parametrize("raw,expected", [
    ("08123456789", "+628123456789"),
    ("081234567890", "+6281234567890"),
    ("+62 21 555 1234", "+62215551234"),
    ("62 21 555 1234", "+62215551234"),
    ("6281234567890", "+6281234567890"),
    ("021-5551234", "+62215551234"),
    ("(031) 1234567", "+62311234567"),
    (None, None),
    ("", None),
    ("invalid", None),
    ("000", None),
])
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_normalize_phones_batch():
    records = [
        {"place_id": "id1", "phone": "08123456789"},
        {"place_id": "id2", "phone": "invalid"},
        {"place_id": "id3", "phone": None},
    ]
    result = normalize_phones_batch(records)
    assert result["id1"] == "+628123456789"
    assert result["id2"] is None
    assert result["id3"] is None


def test_normalize_phones_batch_returns_all_place_ids():
    records = [{"place_id": "a", "phone": "08123456789"}, {"place_id": "b", "phone": None}]
    result = normalize_phones_batch(records)
    assert set(result.keys()) == {"a", "b"}
