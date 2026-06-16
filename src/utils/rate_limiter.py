import asyncio
import random

from config.settings import settings


class RateLimiter:
    """Throttle requests untuk menghindari block dari Google / target website."""

    async def wait(self) -> None:
        """Delay utama — antara klik listing atau request ke website."""
        delay = random.uniform(settings.min_delay_seconds, settings.max_delay_seconds)
        await asyncio.sleep(delay)

    async def wait_short(self) -> None:
        """Delay pendek — antara scroll atau operasi intra-page."""
        await asyncio.sleep(random.uniform(0.3, 0.8))

    async def wait_long(self) -> None:
        """Delay panjang — setelah error atau sebelum retry."""
        await asyncio.sleep(random.uniform(5.0, 10.0))


rate_limiter = RateLimiter()
