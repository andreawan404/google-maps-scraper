"""
Ekstraksi data dari halaman Google Maps detail panel.
SEMUA selector dikumpulkan di SELECTORS dict — update di sini jika Google ganti selector.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple
from playwright.async_api import Page
from src.utils.logger import logger


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BusinessRaw:
    place_id: str
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    maps_url: str = ""
    scraped_at: datetime = field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# SELECTOR DICTIONARY — Update di sini jika selector Google Maps berubah!
# ─────────────────────────────────────────────────────────────────────────────

SELECTORS = {
    # Results panel (kiri)
    "results_feed": 'div[role="feed"]',
    "result_item": "div.Nv2PK",
    "result_item_link": "a.hfpxzc",

    # Detail panel (kanan / overlay)
    "name": "h1.DUwDvf",
    "category": "button.DkEaL",
    "address": 'button[data-item-id="address"]',
    "phone": 'button[data-item-id^="phone"]',
    "website": 'a[data-item-id="authority"]',
    "rating": "div.F7nice > span:first-child",
    "review_count": "div.F7nice > span:last-child",

    # Loading indicators
    "loading_spinner": 'div[jsaction*="loading"]',
    "no_results": "div.dGM0Re",
}


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTORS
# ─────────────────────────────────────────────────────────────────────────────

class ExtractorError(Exception):
    """Raised ketika field wajib tidak bisa diekstrak."""
    pass


async def extract_business_from_page(page: Page) -> BusinessRaw:
    """
    Ekstrak semua field dari detail panel yang sedang terbuka di page.
    Field wajib: name (jika tidak ada, raise ExtractorError).
    Semua field lain: best-effort (None jika tidak ketemu).
    """
    current_url = page.url

    # ── Name (wajib) ──────────────────────────────────────────────────────
    name = await _get_text(page, SELECTORS["name"])
    if not name:
        raise ExtractorError(f"Cannot extract name from: {current_url}")

    # ── Place ID ──────────────────────────────────────────────────────────
    place_id = _extract_place_id(current_url) or _generate_fallback_id(name, current_url)

    # ── Koordinat dari URL ─────────────────────────────────────────────────
    lat, lng = _extract_coords_from_url(current_url) or (None, None)

    # ── Category ──────────────────────────────────────────────────────────
    category = await _get_text(page, SELECTORS["category"])

    # ── Address ───────────────────────────────────────────────────────────
    address = await _get_aria_label(page, SELECTORS["address"])
    if not address:
        address = await _get_text(page, SELECTORS["address"])

    # ── Phone ─────────────────────────────────────────────────────────────
    phone_raw = await _get_aria_label(page, SELECTORS["phone"])
    if not phone_raw:
        phone_raw = await _get_text(page, SELECTORS["phone"])
    phone = _clean_phone(phone_raw)

    # ── Website ───────────────────────────────────────────────────────────
    website = await _get_href(page, SELECTORS["website"])

    # ── Rating ────────────────────────────────────────────────────────────
    rating_text = await _get_text(page, SELECTORS["rating"])
    rating = _parse_float(rating_text)

    # ── Review Count ─────────────────────────────────────────────────────
    review_text = await _get_text(page, SELECTORS["review_count"])
    review_count = _parse_review_count(review_text)

    business = BusinessRaw(
        place_id=place_id,
        name=name.strip(),
        category=category,
        address=address,
        phone=phone,
        website=website,
        rating=rating,
        review_count=review_count,
        latitude=lat,
        longitude=lng,
        maps_url=current_url,
    )

    logger.debug("Extracted: {} | phone={} | lat={}", name, phone, lat)
    return business


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def _get_text(page: Page, selector: str) -> Optional[str]:
    try:
        el = await page.query_selector(selector)
        if el:
            return await el.inner_text()
    except Exception:
        pass
    return None


async def _get_aria_label(page: Page, selector: str) -> Optional[str]:
    try:
        el = await page.query_selector(selector)
        if el:
            label = await el.get_attribute("aria-label")
            return label
    except Exception:
        pass
    return None


async def _get_href(page: Page, selector: str) -> Optional[str]:
    try:
        el = await page.query_selector(selector)
        if el:
            href = await el.get_attribute("href")
            # Bersihkan Google redirect URL
            if href and "google.com/url" in href:
                match = re.search(r'[?&]q=([^&]+)', href)
                if match:
                    from urllib.parse import unquote
                    return unquote(match.group(1))
            return href
    except Exception:
        pass
    return None


def _extract_place_id(url: str) -> Optional[str]:
    """Ekstrak Place ID dari URL Google Maps."""
    # Format: /place/NAME/data=...!1s0x...:0x...
    match = re.search(r'!1s([^!]+)', url)
    if match:
        return match.group(1)

    # Format alternatif: placeid=...
    match = re.search(r'placeid=([^&]+)', url)
    if match:
        return match.group(1)

    return None


def _extract_coords_from_url(url: str) -> Optional[Tuple[float, float]]:
    """Ekstrak koordinat dari URL format @lat,lng,zoom."""
    match = re.search(r'@(-?\d+\.?\d*),(-?\d+\.?\d*)', url)
    if match:
        try:
            return float(match.group(1)), float(match.group(2))
        except ValueError:
            pass
    return None


def _generate_fallback_id(name: str, url: str) -> str:
    """Buat ID unik dari hash nama + URL jika place_id tidak ditemukan."""
    import hashlib
    raw = f"{name}|{url}"
    return "hash_" + hashlib.md5(raw.encode()).hexdigest()[:16]


def _clean_phone(raw: Optional[str]) -> Optional[str]:
    """Bersihkan string phone dari prefix aria-label Google."""
    if not raw:
        return None
    # Hapus prefix seperti "Phone: " atau "Telepon: "
    raw = re.sub(r'^(Phone|Telepon|Tel|Telp)[:\s]+', '', raw, flags=re.IGNORECASE)
    # Hapus karakter non-digit kecuali + dan -
    cleaned = re.sub(r'[^\d+\-\s()]', '', raw).strip()
    return cleaned if cleaned else None


def _parse_float(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    text = text.replace(',', '.').strip()
    match = re.search(r'(\d+\.?\d*)', text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def _parse_review_count(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    # "1.234 ulasan" → 1234
    text = re.sub(r'[.\s](?=\d{3})', '', text)
    match = re.search(r'(\d+)', text.replace(',', ''))
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None
