"""Cache manager initialization."""
from __future__ import annotations

from app.config import settings
from .cache_manager import CacheManager
from .cache_backends.memory import MemoryCacheBackend
from .cache_backends.sqlite import SQLiteCacheBackend

cache_manager = CacheManager()


async def init_cache() -> CacheManager:
    if not settings.cache_enabled:
        cache_manager.configure(None, None, enabled=False)
        return cache_manager

    l1_cache = MemoryCacheBackend(default_max_size=settings.cache_l1_max_size)
    l2_cache = None

    if settings.cache_l2_enabled:
        settings.cache_sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        l2_cache = SQLiteCacheBackend(db_path=str(settings.cache_sqlite_path))
        await l2_cache.initialize()

    cache_manager.configure(l1_cache, l2_cache, enabled=True)

    if settings.cache_l2_enabled and settings.cache_sqlite_cleanup_interval > 0:
        await cache_manager.start_cleanup_task(settings.cache_sqlite_cleanup_interval)

    return cache_manager


async def shutdown_cache() -> None:
    await cache_manager.close()
