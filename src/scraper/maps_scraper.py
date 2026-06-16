from typing import AsyncGenerator, Optional
from urllib.parse import quote_plus

from playwright.async_api import Browser, BrowserContext, Page

from src.scraper.browser import browser_session, create_context, new_stealth_page
from src.scraper.extractor import (
    SELECTORS,
    BusinessRaw,
    ExtractorError,
    extract_business_from_page,
)
from src.utils.logger import logger
from src.utils.rate_limiter import rate_limiter


class CaptchaError(Exception):
    """Raised jika Google menampilkan CAPTCHA challenge."""
    pass


async def scrape_google_maps(
    keyword: str,
    location: str,
    max_results: int = 100,
    proxy: Optional[str] = None,
) -> AsyncGenerator[BusinessRaw, None]:
    """
    Async generator — yield BusinessRaw satu per satu saat ditemukan.

    Dua fase:
      1. Scroll halaman search → kumpulkan semua URL listing
      2. Buka tiap URL via page.goto() → ekstrak data

    Strategi goto lebih reliable daripada klik karena menghindari masalah
    element visibility, popup, dan race condition saat scroll.
    """
    search_query = quote_plus(f"{keyword} {location}")
    url = f"https://www.google.com/maps/search/{search_query}"

    async with browser_session(proxy) as browser:
        context = await create_context(browser)

        # ── Fase 1: Kumpulkan URL listing ──────────────────────────────────
        search_page = await new_stealth_page(context)
        listing_urls = await _collect_listing_urls(search_page, url, max_results)
        await search_page.close()

        if not listing_urls:
            logger.warning("Tidak ada listing ditemukan untuk: {} {}", keyword, location)
            return

        logger.info("Ditemukan {} listing URL, mulai ekstrak data...", len(listing_urls))

        # ── Fase 2: Ekstrak data tiap listing via goto ──────────────────────
        collected = 0
        for listing_url in listing_urls:
            detail_page = await new_stealth_page(context)
            try:
                await rate_limiter.wait()
                await detail_page.goto(listing_url, wait_until="domcontentloaded", timeout=20000)

                try:
                    await detail_page.wait_for_selector(SELECTORS["name"], timeout=10000)
                except Exception:
                    logger.debug("Detail panel tidak muncul: {}", listing_url[:80])
                    continue

                await _check_captcha(detail_page)

                business = await extract_business_from_page(detail_page)
                collected += 1
                logger.debug("[{}/{}] {}", collected, len(listing_urls), business.name)
                yield business

            except CaptchaError:
                raise
            except ExtractorError as e:
                logger.debug("Skip listing (ExtractorError): {}", e)
            except Exception as e:
                logger.warning("Error ekstrak {}: {}", listing_url[:80], e)
            finally:
                try:
                    await detail_page.close()
                except Exception:
                    pass

        logger.info("Scraping selesai. Total diekstrak: {}", collected)


async def _collect_listing_urls(
    page: Page,
    search_url: str,
    max_results: int,
) -> list[str]:
    """
    Buka halaman search, scroll sampai cukup listing terkumpul.
    Return list URL listing (deduplicated).
    """
    logger.info("Navigasi ke: {}", search_url)
    await page.goto(search_url, wait_until="domcontentloaded")
    await rate_limiter.wait()

    await _check_captcha(page)

    try:
        await page.wait_for_selector(SELECTORS["results_feed"], timeout=15000)
    except Exception:
        logger.warning("Results feed tidak muncul. URL: {}", search_url)
        return []

    collected_urls: list[str] = []
    seen: set[str] = set()
    stale_count = 0

    while len(collected_urls) < max_results:
        items = await page.query_selector_all(SELECTORS["result_item"])
        new_this_round = 0

        for item in items:
            if len(collected_urls) >= max_results:
                break
            link_el = await item.query_selector(SELECTORS["result_item_link"])
            if not link_el:
                continue
            href = await link_el.get_attribute("href") or ""
            # Normalisasi: hapus query params agar deduplikasi akurat
            href_clean = href.split("?")[0] if href else ""
            if href_clean and href_clean not in seen:
                seen.add(href_clean)
                collected_urls.append(href)
                new_this_round += 1

        logger.debug("Scroll: {} URL terkumpul (+{} baru)", len(collected_urls), new_this_round)

        if await page.query_selector(SELECTORS["no_results"]):
            logger.info("Semua hasil sudah ditampilkan.")
            break

        if new_this_round == 0:
            stale_count += 1
            if stale_count >= 3:
                logger.info("Tidak ada URL baru setelah 3x scroll, berhenti.")
                break
        else:
            stale_count = 0

        # Scroll feed ke bawah
        feed = await page.query_selector(SELECTORS["results_feed"])
        if feed:
            await feed.evaluate("el => el.scrollBy(0, 800)")
        else:
            await page.evaluate("window.scrollBy(0, 800)")

        await rate_limiter.wait_short()
        await _check_captcha(page)

    return collected_urls[:max_results]


async def _check_captcha(page: Page) -> None:
    """Raise CaptchaError jika halaman menampilkan reCAPTCHA."""
    if await page.query_selector("iframe[src*='recaptcha']"):
        raise CaptchaError("CAPTCHA terdeteksi. Ganti IP atau gunakan proxy.")
