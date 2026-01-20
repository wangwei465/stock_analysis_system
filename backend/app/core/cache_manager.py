"""Unified cache manager with L1/L2 backends."""
from __future__ import annotations

import asyncio
import inspect
import threading
from abc import ABC, abstractmethod
from datetime import timedelta
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

T = TypeVar("T")


class CacheLevel(Enum):
    """Cache level."""

    L1_MEMORY = "memory"
    L2_SQLITE = "sqlite"
    BOTH = "both"


class CacheConfig:
    """Cache configuration."""

    def __init__(
        self,
        ttl: timedelta,
        max_size: int = 1000,
        level: CacheLevel = CacheLevel.L1_MEMORY,
        namespace: str = "default",
        serialize: bool = True,
    ):
        self.ttl = ttl
        self.max_size = max_size
        self.level = level
        self.namespace = namespace
        self.serialize = serialize


class CacheBackend(ABC):
    """Cache backend interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: timedelta) -> bool:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear_namespace(self, namespace: str) -> int:
        pass


class CacheStats:
    """Cache statistics."""

    def __init__(self):
        self.l1_hits = 0
        self.l2_hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def record_hit(self, level: str) -> None:
        with self._lock:
            if level == "L1":
                self.l1_hits += 1
            else:
                self.l2_hits += 1

    def record_miss(self) -> None:
        with self._lock:
            self.misses += 1

    @property
    def hit_rate(self) -> float:
        total = self.l1_hits + self.l2_hits + self.misses
        return (self.l1_hits + self.l2_hits) / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "l1_hits": self.l1_hits,
                "l2_hits": self.l2_hits,
                "misses": self.misses,
                "hit_rate": round(self.hit_rate * 100, 2),
            }


class CacheManager:
    """Unified cache manager."""

    _instance: Optional["CacheManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._l1_cache: Optional[CacheBackend] = None
        self._l2_cache: Optional[CacheBackend] = None
        self._enabled = True
        self._stats = CacheStats()
        self._cleanup_task: Optional[asyncio.Task] = None

    def configure(
        self,
        l1_cache: Optional[CacheBackend],
        l2_cache: Optional[CacheBackend],
        enabled: bool = True,
    ) -> None:
        self._l1_cache = l1_cache
        self._l2_cache = l2_cache
        self._enabled = enabled

    async def get(
        self,
        key: str,
        config: CacheConfig,
        fetch_func: Optional[Callable[[], T]] = None,
    ) -> Optional[T]:
        """Get cache value, with optional fetch fallback."""
        if not self._enabled:
            return await self._fetch_fallback(fetch_func)

        full_key = self._build_key(key, config.namespace)

        if config.level in (CacheLevel.L1_MEMORY, CacheLevel.BOTH) and self._l1_cache:
            value = await self._l1_cache.get(full_key)
            if value is not None:
                self._stats.record_hit("L1")
                return value

        if config.level in (CacheLevel.L2_SQLITE, CacheLevel.BOTH) and self._l2_cache:
            value = await self._l2_cache.get(full_key)
            if value is not None:
                self._stats.record_hit("L2")
                if config.level == CacheLevel.BOTH and self._l1_cache:
                    await self._l1_cache.set(full_key, value, config.ttl)
                return value

        self._stats.record_miss()
        if fetch_func:
            value = await self._fetch_fallback(fetch_func)
            if value is not None:
                await self.set(key, value, config)
            return value

        return None

    async def set(self, key: str, value: Any, config: CacheConfig) -> bool:
        """Set cache value."""
        if not self._enabled:
            return True

        full_key = self._build_key(key, config.namespace)
        success = True

        if config.level in (CacheLevel.L1_MEMORY, CacheLevel.BOTH) and self._l1_cache:
            success &= await self._l1_cache.set(full_key, value, config.ttl)
        if config.level in (CacheLevel.L2_SQLITE, CacheLevel.BOTH) and self._l2_cache:
            success &= await self._l2_cache.set(full_key, value, config.ttl)

        return success

    async def clear_namespace(self, namespace: str) -> int:
        total = 0
        if self._l1_cache:
            total += await self._l1_cache.clear_namespace(namespace)
        if self._l2_cache:
            total += await self._l2_cache.clear_namespace(namespace)
        return total

    def get_stats(self) -> dict:
        return self._stats.to_dict()

    async def start_cleanup_task(self, interval_seconds: int) -> None:
        if not self._l2_cache or interval_seconds <= 0 or self._cleanup_task:
            return
        if not hasattr(self._l2_cache, "purge_expired"):
            return

        async def _cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    await self._l2_cache.purge_expired()
                except asyncio.CancelledError:
                    break
                except Exception:
                    await asyncio.sleep(interval_seconds)

        self._cleanup_task = asyncio.create_task(_cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def close(self) -> None:
        await self.stop_cleanup_task()
        if self._l2_cache and hasattr(self._l2_cache, "close"):
            await self._l2_cache.close()

    def get_sync(
        self,
        key: str,
        config: CacheConfig,
        fetch_func: Optional[Callable[[], T]] = None,
    ) -> Optional[T]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.get(key, config, fetch_func))
        raise RuntimeError("CacheManager.get_sync must not be called in a running event loop")

    def _build_key(self, key: str, namespace: str) -> str:
        return f"{namespace}:{key}"

    async def _fetch_fallback(self, fetch_func: Optional[Callable[[], T]]) -> Optional[T]:
        if fetch_func is None:
            return None
        if inspect.iscoroutinefunction(fetch_func):
            return await fetch_func()
        result = fetch_func()
        if inspect.isawaitable(result):
            return await result
        return result
