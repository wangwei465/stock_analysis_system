"""In-memory cache backend using cachetools."""
from __future__ import annotations

from cachetools import TTLCache
from datetime import timedelta
from typing import Any, Dict, Optional
import threading

from ..cache_manager import CacheBackend


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend."""

    def __init__(self, default_max_size: int = 10000):
        self._caches: Dict[str, TTLCache] = {}
        self._lock = threading.RLock()
        self._default_max_size = default_max_size

    def _get_or_create_cache(self, namespace: str, ttl: timedelta, max_size: int) -> TTLCache:
        cache_key = f"{namespace}:{int(ttl.total_seconds())}"
        with self._lock:
            if cache_key not in self._caches:
                self._caches[cache_key] = TTLCache(
                    maxsize=max_size,
                    ttl=ttl.total_seconds(),
                )
            return self._caches[cache_key]

    async def get(self, key: str) -> Optional[Any]:
        with self._lock:
            for cache in self._caches.values():
                if key in cache:
                    return cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: timedelta) -> bool:
        try:
            namespace = key.split(":", 1)[0] if ":" in key else "default"
            cache = self._get_or_create_cache(namespace, ttl, self._default_max_size)
            with self._lock:
                cache[key] = value
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        with self._lock:
            for cache in self._caches.values():
                if key in cache:
                    del cache[key]
                    return True
        return False

    async def exists(self, key: str) -> bool:
        with self._lock:
            for cache in self._caches.values():
                if key in cache:
                    return True
        return False

    async def clear_namespace(self, namespace: str) -> int:
        with self._lock:
            count = 0
            keys_to_delete = []
            for cache_key, cache in self._caches.items():
                if cache_key.startswith(f"{namespace}:"):
                    count += len(cache)
                    keys_to_delete.append(cache_key)

            for key in keys_to_delete:
                del self._caches[key]

        return count
