"""FastAPI Application Entry Point"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.v1.router import api_router
from .config import settings
from .core.cache_setup import init_cache, shutdown_cache
from .core.cache_warmer import CacheWarmer
from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    await init_db()
    await init_cache()
    if settings.cache_warm_on_startup:
        warmer = CacheWarmer()
        asyncio.create_task(warmer.warm_on_startup())
    yield
    # Shutdown
    await shutdown_cache()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.1.0"}
