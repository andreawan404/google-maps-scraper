from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Browser
    headless: bool = Field(True)
    browser_timeout: int = Field(30000)

    # Rate limiting
    min_delay_seconds: float = Field(2.0)
    max_delay_seconds: float = Field(5.0)

    # Database
    database_url: str = Field("sqlite:///output/scraper.db")

    # Proxy
    proxy_list: str = Field("")

    # Logging
    log_level: str = Field("INFO")
    log_file: str = Field("output/scraper.log")

    # Email finder
    email_timeout_seconds: int = Field(10)
    max_email_per_site: int = Field(3)

    # Retry
    max_retries: int = Field(3)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
