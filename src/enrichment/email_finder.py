import asyncio
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from config.settings import settings
from src.utils.logger import logger
from src.utils.rate_limiter import rate_limiter

_EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

_BLACKLIST_KEYWORDS = {"noreply", "no-reply", "example", "sentry", "wixpress", "wordpress", "w3.org"}
_BLACKLIST_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
_CONTACT_PATHS = ["/contact", "/kontak", "/hubungi-kami", "/about", "/tentang-kami", "/about-us"]

_SEMAPHORE = asyncio.Semaphore(5)  # Max 5 concurrent HTTP requests


async def find_emails_for_businesses(
    businesses: list[dict],
) -> dict[str, Optional[str]]:
    """
    Cari email untuk setiap bisnis yang punya website.
    Return: {place_id: email_terbaik_atau_None}
    """
    async with httpx.AsyncClient(
        timeout=settings.email_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; GoogleMapsScraper/1.0)"},
        verify=False,
    ) as client:
        tasks = [
            _find_one(client, b["place_id"], b.get("name", ""), b["website"])
            for b in businesses
            if b.get("website")
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    results: dict[str, Optional[str]] = {}
    for b, result in zip(businesses, raw_results):
        if isinstance(result, Exception):
            logger.debug("Email finder error untuk '{}': {}", b.get("name"), result)
            results[b["place_id"]] = None
        else:
            results[b["place_id"]] = result

    return results


async def _find_one(
    client: httpx.AsyncClient,
    place_id: str,
    name: str,
    website: str,
) -> Optional[str]:
    async with _SEMAPHORE:
        await rate_limiter.wait_short()
        domain = urlparse(website).netloc.replace("www.", "")

        emails = await _fetch_emails(client, website)

        if not emails:
            for path in _CONTACT_PATHS:
                contact_url = urljoin(website, path)
                try:
                    emails = await _fetch_emails(client, contact_url)
                    if emails:
                        logger.debug("Email ditemukan di {} untuk '{}'", contact_url, name)
                        break
                except Exception:
                    continue

        best = _best_email(emails, domain)
        if best:
            logger.debug("Email terbaik untuk '{}': {}", name, best)
        return best


async def _fetch_emails(client: httpx.AsyncClient, url: str) -> list[str]:
    try:
        resp = await client.get(url)
        if resp.status_code >= 400:
            return []

        soup = BeautifulSoup(resp.text, "lxml")

        # Prioritas: mailto links (lebih akurat dari regex)
        found: list[str] = []
        for a in soup.select("a[href^='mailto:']"):
            href = a.get("href", "")
            email = href.replace("mailto:", "").split("?")[0].strip()
            if email and "@" in email:
                found.append(email)

        # Fallback: regex pada teks halaman
        text = soup.get_text(" ", strip=True)
        found += _EMAIL_REGEX.findall(text)

        # Deduplicate, jaga urutan, filter invalid
        seen: set[str] = set()
        result: list[str] = []
        for e in found:
            if e not in seen and _is_valid_email(e):
                seen.add(e)
                result.append(e)

        return result

    except Exception as e:
        logger.debug("Fetch gagal {}: {}", url, e)
        return []


def _is_valid_email(email: str) -> bool:
    lower = email.lower()
    if any(b in lower for b in _BLACKLIST_KEYWORDS):
        return False
    if any(lower.endswith(ext) for ext in _BLACKLIST_EXTENSIONS):
        return False
    parts = lower.split("@")
    return len(parts) == 2 and "." in parts[1] and len(parts[1]) > 3


def _best_email(emails: list[str], domain: str) -> Optional[str]:
    if not emails:
        return None

    _PREFERRED_LOCALS = {"info", "contact", "hello", "halo", "admin", "cs", "sales", "marketing"}
    _PENALTY_LOCALS = {"support", "help", "noreply", "no-reply", "donotreply"}

    def score(email: str) -> int:
        local = email.split("@")[0].lower()
        s = 0
        if domain and domain in email.lower():
            s += 10
        if local in _PREFERRED_LOCALS:
            s += 5
        if local in _PENALTY_LOCALS:
            s -= 15
        return s

    return max(emails, key=score)
