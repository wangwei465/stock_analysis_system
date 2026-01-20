"""Cache monitoring utilities."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from .cache_manager import CacheManager

logger = logging.getLogger("cache")


class CacheMonitor:
    """Cache health monitor."""

    def __init__(self, alert_threshold: float = 0.5):
        self._alert_threshold = alert_threshold
        self._last_alert_time = None

    async def check_health(self) -> dict:
        cache = CacheManager()
        stats = cache.get_stats()

        health = {
            "status": "healthy",
            "hit_rate": stats["hit_rate"],
            "l1_hits": stats["l1_hits"],
            "l2_hits": stats["l2_hits"],
            "misses": stats["misses"],
            "timestamp": datetime.now().isoformat(),
        }

        if stats["hit_rate"] < self._alert_threshold * 100:
            health["status"] = "warning"
            health["message"] = f"Cache hit rate below {self._alert_threshold * 100}%"
            self._trigger_alert(health)

        return health

    def _trigger_alert(self, health: dict) -> None:
        now = datetime.now()
        if self._last_alert_time is None or now - self._last_alert_time > timedelta(minutes=5):
            logger.warning("Cache health warning: %s", health)
            self._last_alert_time = now
