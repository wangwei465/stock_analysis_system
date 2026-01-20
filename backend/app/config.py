"""Application configuration"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # App
    app_name: str = "Stock Analysis System"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/stock.db"

    # Cache
    cache_ttl: int = 300  # 5 minutes (legacy)
    cache_enabled: bool = True
    cache_l1_max_size: int = 10000
    cache_l2_enabled: bool = True
    cache_sqlite_path: Path = Path(__file__).parent.parent / "data" / "cache.db"
    cache_sqlite_cleanup_interval: int = 3600

    # Cache TTL settings (seconds)
    cache_ttl_stock_list: int = 14400      # 4 hours
    cache_ttl_kline_history: int = 86400   # 24 hours
    cache_ttl_kline_today: int = 300       # 5 minutes
    cache_ttl_realtime: int = 3            # 3 seconds
    cache_ttl_intraday: int = 60           # 60 seconds
    cache_ttl_fundamental: int = 21600     # 6 hours
    cache_ttl_market_snapshot: int = 300   # 5 minutes

    # Cache warm settings
    cache_warm_on_startup: bool = True
    cache_warm_popular_stocks: List[str] = [
        "000001.SZ",
        "600519.SH",
        "000858.SZ",
    ]

    # Data paths
    base_dir: Path = Path(__file__).parent.parent
    data_dir: Path = base_dir / "data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
