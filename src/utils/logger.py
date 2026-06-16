import sys
from loguru import logger


def _setup_logger() -> None:
    logger.remove()

    from config.settings import settings

    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=None,  # Auto-detect: warna hanya jika terminal mendukung
    )

    if settings.log_file:
        logger.add(
            settings.log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} — {message}",
            rotation="00:00",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
        )


_setup_logger()

__all__ = ["logger"]
