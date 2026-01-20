"""Cache warm-up utilities."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from app.config import settings
from .data_fetcher import StockDataFetcher
from .stock_screener import StockScreener


class CacheWarmer:
    """Cache warm-up manager."""

    def __init__(self):
        self._is_warming = False

    async def warm_on_startup(self) -> None:
        if self._is_warming or not settings.cache_enabled:
            return
        self._is_warming = True

        try:
            await self._warm_stock_list()
            await self._warm_popular_stocks()
            await self._warm_market_snapshot()
        finally:
            self._is_warming = False

    async def _warm_stock_list(self) -> None:
        await StockDataFetcher.get_stock_list_async()

    async def _warm_popular_stocks(self) -> None:
        popular_codes = settings.cache_warm_popular_stocks or []
        if not popular_codes:
            return

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        tasks = [
            StockDataFetcher.get_daily_kline_async(code, start_date, end_date)
            for code in popular_codes
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _warm_market_snapshot(self) -> None:
        await StockScreener.get_all_stocks_data()
