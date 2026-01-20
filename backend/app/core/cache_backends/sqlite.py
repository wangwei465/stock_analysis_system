"""SQLite cache backend (persistent)."""
from __future__ import annotations

import asyncio
import pickle
import time
from datetime import timedelta
from typing import Any, Optional

import aiosqlite

from ..cache_manager import CacheBackend


class SQLiteCacheBackend(CacheBackend):
    """SQLite cache backend."""

    def __init__(self, db_path: str = "./data/cache.db"):
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        await self._ensure_conn()

    async def _ensure_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._db_path)
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.execute("PRAGMA synchronous=NORMAL;")
            await self._conn.execute("PRAGMA busy_timeout=5000;")
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    value BLOB NOT NULL,
                    expires_at INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                )
                """
            )
            await self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at)"
            )
            await self._conn.commit()
        return self._conn

    async def get(self, key: str) -> Optional[Any]:
        conn = await self._ensure_conn()
        async with self._lock:
            cursor = await conn.execute(
                "SELECT value, expires_at FROM cache_entries WHERE key = ?",
                (key,),
            )
            row = await cursor.fetchone()
            await cursor.close()
            if not row:
                return None
            value_blob, expires_at = row
            if expires_at <= int(time.time()):
                await conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                await conn.commit()
                return None
            return pickle.loads(value_blob)

    async def set(self, key: str, value: Any, ttl: timedelta) -> bool:
        conn = await self._ensure_conn()
        expires_at = int(time.time() + ttl.total_seconds())
        payload = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        async with self._lock:
            await conn.execute(
                """
                INSERT INTO cache_entries (key, value, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, expires_at=excluded.expires_at
                """,
                (key, payload, expires_at, int(time.time())),
            )
            await conn.commit()
        return True

    async def delete(self, key: str) -> bool:
        conn = await self._ensure_conn()
        async with self._lock:
            cursor = await conn.execute(
                "DELETE FROM cache_entries WHERE key = ?",
                (key,),
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def exists(self, key: str) -> bool:
        conn = await self._ensure_conn()
        async with self._lock:
            cursor = await conn.execute(
                "SELECT 1 FROM cache_entries WHERE key = ? AND expires_at > ?",
                (key, int(time.time())),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return row is not None

    async def clear_namespace(self, namespace: str) -> int:
        conn = await self._ensure_conn()
        async with self._lock:
            cursor = await conn.execute(
                "DELETE FROM cache_entries WHERE key LIKE ?",
                (f"{namespace}:%",),
            )
            await conn.commit()
            return cursor.rowcount

    async def purge_expired(self) -> int:
        conn = await self._ensure_conn()
        async with self._lock:
            cursor = await conn.execute(
                "DELETE FROM cache_entries WHERE expires_at <= ?",
                (int(time.time()),),
            )
            await conn.commit()
            return cursor.rowcount

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
