"""Cache management API endpoints."""
import asyncio
from datetime import datetime

from fastapi import APIRouter

from app.core.cache_manager import CacheManager
from app.core.cache_warmer import CacheWarmer

router = APIRouter()


@router.get("/stats")
async def get_cache_stats():
    cache = CacheManager()
    return {
        "status": "ok",
        "stats": cache.get_stats(),
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/clear/{namespace}")
async def clear_cache(namespace: str):
    cache = CacheManager()
    count = await cache.clear_namespace(namespace)
    return {
        "status": "ok",
        "cleared_count": count,
        "namespace": namespace,
    }


@router.post("/warm")
async def trigger_warm():
    warmer = CacheWarmer()
    asyncio.create_task(warmer.warm_on_startup())
    return {"status": "ok", "message": "Warm-up started"}
