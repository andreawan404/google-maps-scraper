import pytest

from src.scraper.extractor import (
    _clean_phone,
    _extract_coords_from_url,
    _extract_place_id,
    _generate_fallback_id,
    _parse_float,
    _parse_review_count,
)


def test_extract_place_id_from_data_param():
    url = "https://www.google.com/maps/place/Apotek/@-6.9147,107.6089,17z/data=!4m6!3m5!1sChIJtest123"
    assert _extract_place_id(url) == "ChIJtest123"


def test_extract_place_id_from_placeid_query():
    url = "https://maps.google.com/?placeid=ChIJabc456"
    assert _extract_place_id(url) == "ChIJabc456"


def test_extract_place_id_returns_none_for_plain_url():
    assert _extract_place_id("https://example.com") is None


def test_extract_coords_standard_format():
    url = "https://www.google.com/maps/place/test/@-6.9147,107.6089,17z"
    lat, lng = _extract_coords_from_url(url)
    assert abs(lat - (-6.9147)) < 0.001
    assert abs(lng - 107.6089) < 0.001


def test_extract_coords_negative_longitude():
    url = "https://www.google.com/maps/place/test/@40.7128,-74.0060,12z"
    lat, lng = _extract_coords_from_url(url)
    assert abs(lat - 40.7128) < 0.001
    assert abs(lng - (-74.006)) < 0.001


def test_extract_coords_returns_none_for_no_match():
    assert _extract_coords_from_url("https://example.com") is None


def test_clean_phone_removes_phone_prefix():
    assert _clean_phone("Phone: +62 21 555 1234") == "+62 21 555 1234"


def test_clean_phone_removes_telepon_prefix():
    assert _clean_phone("Telepon: 022-1234") == "022-1234"


def test_clean_phone_returns_none_for_none():
    assert _clean_phone(None) is None


def test_clean_phone_returns_none_for_empty():
    assert _clean_phone("") is None


def test_parse_float_dot_separator():
    assert _parse_float("4.5") == 4.5


def test_parse_float_comma_separator():
    assert _parse_float("4,5") == 4.5


def test_parse_float_integer():
    assert _parse_float("5") == 5.0


def test_parse_float_returns_none_for_none():
    assert _parse_float(None) is None


def test_parse_float_returns_none_for_text():
    assert _parse_float("tidak ada") is None


def test_parse_review_count_with_dot_thousand_separator():
    assert _parse_review_count("1.234 ulasan") == 1234


def test_parse_review_count_simple_number():
    assert _parse_review_count("50") == 50


def test_parse_review_count_with_comma():
    assert _parse_review_count("1,500 reviews") == 1500


def test_parse_review_count_returns_none_for_none():
    assert _parse_review_count(None) is None


def test_generate_fallback_id_is_deterministic():
    id1 = _generate_fallback_id("Toko ABC", "https://maps.google.com/?q=abc")
    id2 = _generate_fallback_id("Toko ABC", "https://maps.google.com/?q=abc")
    assert id1 == id2


def test_generate_fallback_id_starts_with_hash_prefix():
    result = _generate_fallback_id("Toko ABC", "https://example.com")
    assert result.startswith("hash_")


def test_generate_fallback_id_differs_for_different_inputs():
    id1 = _generate_fallback_id("Toko ABC", "https://maps.google.com/a")
    id2 = _generate_fallback_id("Toko XYZ", "https://maps.google.com/b")
    assert id1 != id2
