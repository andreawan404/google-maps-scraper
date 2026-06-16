import random
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from urllib.parse import urlparse

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from config.settings import settings
from src.utils.logger import logger

_VIEWPORTS = [
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Injeksi JS untuk menyembunyikan tanda-tanda otomasi
_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
Object.defineProperty(navigator, 'languages', {get: () => ['id-ID', 'id', 'en-US', 'en']});
window.chrome = {runtime: {}};
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : originalQuery(parameters);
"""


async def create_browser(playwright: Playwright, proxy: Optional[str] = None) -> Browser:
    proxy_config = _parse_proxy(proxy) if proxy else None
    browser = await playwright.chromium.launch(
        headless=settings.headless,
        proxy=proxy_config,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage",
        ],
    )
    logger.debug("Browser launched: headless={}, proxy={}", settings.headless, bool(proxy))
    return browser


async def create_context(browser: Browser) -> BrowserContext:
    viewport = random.choice(_VIEWPORTS)
    user_agent = random.choice(_USER_AGENTS)
    context = await browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale="id-ID",
        timezone_id="Asia/Jakarta",
    )
    return context


async def new_stealth_page(context: BrowserContext) -> Page:
    """Buat page baru dengan stealth scripts dan timeout dari settings."""
    page = await context.new_page()
    await page.add_init_script(_STEALTH_SCRIPT)
    page.set_default_timeout(settings.browser_timeout)
    return page


@asynccontextmanager
async def browser_session(proxy: Optional[str] = None) -> AsyncGenerator[Browser, None]:
    """Context manager — pastikan browser selalu ter-close meski ada exception."""
    async with async_playwright() as playwright:
        browser = await create_browser(playwright, proxy)
        try:
            yield browser
        finally:
            try:
                await browser.close()
                logger.debug("Browser closed.")
            except Exception as e:
                logger.debug("Browser already closed: {}", e)


def _parse_proxy(proxy_url: str) -> dict:
    parsed = urlparse(proxy_url)
    result: dict = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    if parsed.username:
        result["username"] = parsed.username
        result["password"] = parsed.password or ""
    return result
