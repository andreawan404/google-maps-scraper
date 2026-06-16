import itertools
from typing import Optional
from urllib.parse import urlparse

from config.settings import settings


class ProxyManager:
    """Round-robin rotation dari daftar proxy di PROXY_LIST env var."""

    def __init__(self) -> None:
        raw = settings.proxy_list
        self._proxies = [p.strip() for p in raw.split(",") if p.strip()] if raw else []
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None

    async def next_proxy(self) -> Optional[str]:
        """Return proxy URL berikutnya, atau None jika tidak ada proxy."""
        if not self._cycle:
            return None
        return next(self._cycle)

    def has_proxies(self) -> bool:
        return bool(self._proxies)

    @staticmethod
    def to_playwright_proxy(proxy_url: str) -> dict:
        """Konversi proxy URL string ke dict format Playwright."""
        parsed = urlparse(proxy_url)
        result: dict = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
        if parsed.username:
            result["username"] = parsed.username
            result["password"] = parsed.password or ""
        return result


proxy_manager = ProxyManager()
