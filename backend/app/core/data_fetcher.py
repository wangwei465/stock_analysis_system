"""Stock data fetcher using AKShare"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd

from app.config import settings
from .async_utils import run_sync, run_akshare
from .cache_manager import CacheManager, CacheConfig, CacheLevel

# 延迟导入 AKShare：AKShare 首次 import 可能较慢（依赖多、初始化重），
# 如果在 FastAPI 启动阶段直接导入，会显著拉长冷启动时间；因此这里改为按需加载。
_ak = None

def get_akshare():
    """
    按需加载并缓存 AKShare 模块实例。

    返回值就是 `import akshare as ak` 得到的模块对象，后续通过 `ak.xxx()` 调用具体接口。
    """
    global _ak
    if _ak is None:
        import akshare as ak
        _ak = ak
    return _ak

CACHE_CONFIGS = {
    "stock_list": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_stock_list),
        max_size=1,
        level=CacheLevel.BOTH,
        namespace="stock",
    ),
    "daily_kline_history": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_kline_history),
        max_size=500,
        level=CacheLevel.BOTH,
        namespace="kline",
    ),
    "daily_kline_today": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_kline_today),
        max_size=500,
        level=CacheLevel.L1_MEMORY,
        namespace="kline",
    ),
    "weekly_kline": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_kline_history),
        max_size=300,
        level=CacheLevel.BOTH,
        namespace="kline",
    ),
    "monthly_kline": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_kline_history),
        max_size=200,
        level=CacheLevel.BOTH,
        namespace="kline",
    ),
    "realtime_quote": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_realtime),
        max_size=1000,
        level=CacheLevel.L1_MEMORY,
        namespace="quote",
    ),
    "intraday": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_intraday),
        max_size=500,
        level=CacheLevel.L1_MEMORY,
        namespace="intraday",
    ),
}


class StockDataFetcher:
    """A-share stock data fetcher using AKShare"""

    _cache = CacheManager()

    @staticmethod
    def get_stock_list() -> pd.DataFrame:
        """Get A-share stock list"""
        try:
            ak = get_akshare()
            # AKShare: stock_info_a_code_name 返回 A 股代码与名称等基础信息。
            # 本项目在此基础上补充 market/full_code 字段，用作系统内部统一股票标识。
            df = ak.stock_info_a_code_name()
            # Add market suffix
            df['market'] = df['code'].apply(
                lambda x: 'SH' if x.startswith('6') else 'SZ'
            )
            df['full_code'] = df.apply(
                lambda row: f"{row['code']}.{'SH' if row['code'].startswith('6') else 'SZ'}",
                axis=1
            )
            return df
        except Exception as e:
            print(f"Error fetching stock list: {e}")
            return pd.DataFrame()

    @staticmethod
    def search_stocks(keyword: str, limit: int = 20) -> List[Dict[str, str]]:
        """Search stocks by code or name"""
        df = StockDataFetcher.get_stock_list()
        if df.empty:
            return []

        # Search by code or name
        mask = (
            df['code'].str.contains(keyword, na=False) |
            df['name'].str.contains(keyword, na=False)
        )
        results = df[mask].head(limit)

        return [
            {
                'code': row['full_code'],
                'name': row['name'],
                'market': row['market']
            }
            for _, row in results.iterrows()
        ]

    @staticmethod
    def get_stock_info(code: str) -> Optional[Dict[str, Any]]:
        """Get stock basic info by code"""
        # Extract pure code (remove market suffix)
        pure_code = code.split('.')[0]
        df = StockDataFetcher.get_stock_list()

        if df.empty:
            return None

        row = df[df['code'] == pure_code]
        if row.empty:
            return None

        row = row.iloc[0]
        return {
            'code': code,
            'name': row['name'],
            'market': row['market']
        }

    @staticmethod
    def get_daily_kline(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """
        Get daily K-line data

        Args:
            code: Stock code (e.g., 000001.SZ or 000001)
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            adjust: Adjustment type - qfq(forward), hfq(backward), none

        Returns:
            DataFrame with OHLCV data
        """
        # Extract pure code
        symbol = code.split('.')[0]

        if start_date is None:
            start_date = "20200101"
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            ak = get_akshare()
            # AKShare: stock_zh_a_hist 用于获取历史 K 线数据。
            # - symbol 仅为“纯数字股票代码”，不带 .SZ/.SH 后缀
            # - period 取 daily/weekly/monthly
            # - start_date/end_date 格式为 YYYYMMDD
            # - adjust 取 qfq(前复权)/hfq(后复权)/''(不复权)；AKShare 通常用空串表示不复权
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust if adjust != "none" else ""
            )

            if df.empty:
                return pd.DataFrame()

            # 打印实际列名用于调试
            print(f"[DEBUG] Kline columns for {code}: {list(df.columns)}")

            # 动态列名映射：AKShare 在不同版本/数据源下，列名可能有差异；
            # 这里把中文列名统一映射为英文字段，便于后续计算与前端对接。
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '换手率': 'turnover',
            }
            df = df.rename(columns=column_mapping)

            # 确保必要的列存在
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"[ERROR] Missing columns after mapping: {missing_cols}")
                print(f"[DEBUG] Available columns: {list(df.columns)}")
                return pd.DataFrame()

            # Convert date to datetime
            df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            print(f"Error fetching daily kline for {code}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_weekly_kline(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Get weekly K-line data"""
        symbol = code.split('.')[0]

        if start_date is None:
            start_date = "20200101"
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            ak = get_akshare()
            # 同 get_daily_kline：使用 stock_zh_a_hist 获取“周线”数据（period="weekly"）
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="weekly",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust if adjust != "none" else ""
            )

            if df.empty:
                return pd.DataFrame()

            # 动态列名映射（兼容 AKShare 不同版本返回的列数）
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '换手率': 'turnover',
            }
            df = df.rename(columns=column_mapping)

            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            print(f"Error fetching weekly kline for {code}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_monthly_kline(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Get monthly K-line data"""
        symbol = code.split('.')[0]

        if start_date is None:
            start_date = "20200101"
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        try:
            ak = get_akshare()
            # 同 get_daily_kline：使用 stock_zh_a_hist 获取“月线”数据（period="monthly"）
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="monthly",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust if adjust != "none" else ""
            )

            if df.empty:
                return pd.DataFrame()

            # 动态列名映射（兼容 AKShare 不同版本返回的列数）
            column_mapping = {
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'change_pct',
                '涨跌额': 'change',
                '换手率': 'turnover',
            }
            df = df.rename(columns=column_mapping)

            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])

            return df

        except Exception as e:
            print(f"Error fetching monthly kline for {code}: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_realtime_quote(code: str) -> Optional[Dict[str, Any]]:
        """Get real-time stock quote for a single stock (on-demand)"""
        symbol = code.split('.')[0]

        try:
            ak = get_akshare()
            # AKShare: stock_bid_ask_em 返回单只股票盘口/实时行情（item/value 两列）。
            # 相比 stock_zh_a_spot_em（全市场快照），该接口更轻量，适合“按需查询单股”报价。
            df = ak.stock_bid_ask_em(symbol=symbol)

            if df.empty:
                return None

            # 将 item/value 结构转换为 dict，方便按中文指标名取值。
            data = dict(zip(df['item'], df['value']))

            def safe_float(val, default=0):
                try:
                    return float(val) if val else default
                except (ValueError, TypeError):
                    return default

            def safe_int(val, default=0):
                try:
                    return int(float(val)) if val else default
                except (ValueError, TypeError):
                    return default

            return {
                'code': code,
                'name': data.get('名称', ''),
                'price': safe_float(data.get('最新')),
                'change': safe_float(data.get('涨跌')),
                'change_pct': safe_float(data.get('涨幅')),
                'open': safe_float(data.get('今开')),
                'high': safe_float(data.get('最高')),
                'low': safe_float(data.get('最低')),
                'pre_close': safe_float(data.get('昨收')),
                # 注意：AKShare 返回的“总手”单位通常为“手”（1手=100股），前端如需“股”可再换算。
                'volume': safe_int(data.get('总手')),
                # 注意：金额字段通常为“元”，用于成交额/均价等计算时请保持口径一致。
                'amount': safe_float(data.get('金额')),
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            print(f"Error fetching realtime quote for {code}: {e}")
            return None

    @staticmethod
    def get_intraday_data(code: str) -> pd.DataFrame:
        """
        Get intraday minute data for timeline chart

        Args:
            code: Stock code (e.g., 000001.SZ or 000001)

        Returns:
            DataFrame with minute-level price and volume data
        """
        symbol = code.split('.')[0]
        # AKShare 的 stock_zh_a_minute 接口使用 Sina 行情代码格式：
        # - 上证: sh600000
        # - 深证: sz000001
        if symbol.startswith('6'):
            sina_symbol = f'sh{symbol}'
        else:
            sina_symbol = f'sz{symbol}'

        try:
            ak = get_akshare()
            # AKShare: stock_zh_a_minute 获取分钟线数据。
            # period='1' 表示 1 分钟粒度；adjust='' 表示不复权（分钟线一般也不做复权）。
            df = ak.stock_zh_a_minute(symbol=sina_symbol, period='1', adjust='')

            if df.empty:
                return pd.DataFrame()

            # 接口返回的时间列通常叫 day，这里统一重命名为 time，便于前端/图表组件消费。
            df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']

            # Parse time - the format is like "2024-01-17 09:31:00"
            df['time'] = pd.to_datetime(df['time'])

            # 只取“最新一个交易日”的分时数据（不一定是今天）：
            # - 周末/节假日访问时，AKShare 仍可能返回最近交易日数据
            # - 这里按日期最大值筛选，保证分时图展示口径正确
            if len(df) > 0:
                latest_date = df['time'].dt.date.max()
                df = df[df['time'].dt.date == latest_date]

            # 数值列转换：AKShare 可能返回字符串或包含缺失值，这里统一转为数值，无法解析的置为 NaN。
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            return df

        except Exception as e:
            print(f"Error fetching intraday data for {code}: {e}")
            return pd.DataFrame()

    # ==================== Async versions ====================
    # These methods use run_sync to avoid blocking the event loop

    @staticmethod
    async def get_stock_list_async() -> pd.DataFrame:
        """Async version of get_stock_list"""
        config = CACHE_CONFIGS["stock_list"]

        async def fetch() -> pd.DataFrame:
            return await run_akshare(StockDataFetcher.get_stock_list)

        result = await StockDataFetcher._cache.get("stock_list", config, fetch)
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    async def search_stocks_async(keyword: str, limit: int = 20) -> List[Dict[str, str]]:
        """Async version of search_stocks"""
        df = await StockDataFetcher.get_stock_list_async()
        if df.empty:
            return []

        def _filter() -> List[Dict[str, str]]:
            mask = (
                df['code'].str.contains(keyword, na=False) |
                df['name'].str.contains(keyword, na=False)
            )
            results = df[mask].head(limit)
            return [
                {
                    'code': row['full_code'],
                    'name': row['name'],
                    'market': row['market']
                }
                for _, row in results.iterrows()
            ]

        return await run_sync(_filter)

    @staticmethod
    async def get_stock_info_async(code: str) -> Optional[Dict[str, Any]]:
        """Async version of get_stock_info"""
        df = await StockDataFetcher.get_stock_list_async()
        if df.empty:
            return None

        def _find() -> Optional[Dict[str, Any]]:
            pure_code = code.split('.')[0]
            row = df[df['code'] == pure_code]
            if row.empty:
                return None
            row = row.iloc[0]
            return {
                'code': code,
                'name': row['name'],
                'market': row['market']
            }

        return await run_sync(_find)

    @staticmethod
    async def get_daily_kline_async(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Async version of get_daily_kline"""
        if start_date is None:
            start_date = "20200101"
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        today = datetime.now().strftime("%Y%m%d")
        is_today_included = end_date >= today
        config = CACHE_CONFIGS["daily_kline_today"] if is_today_included else CACHE_CONFIGS["daily_kline_history"]
        cache_key = f"daily:{code}:{start_date}:{end_date}:{adjust}"

        async def fetch() -> pd.DataFrame:
            return await run_akshare(
                StockDataFetcher.get_daily_kline,
                code, start_date, end_date, adjust
            )

        result = await StockDataFetcher._cache.get(cache_key, config, fetch)
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    async def get_weekly_kline_async(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Async version of get_weekly_kline"""
        if start_date is None:
            start_date = "20200101"
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        config = CACHE_CONFIGS["weekly_kline"]
        cache_key = f"weekly:{code}:{start_date}:{end_date}:{adjust}"

        async def fetch() -> pd.DataFrame:
            return await run_akshare(
                StockDataFetcher.get_weekly_kline,
                code, start_date, end_date, adjust
            )

        result = await StockDataFetcher._cache.get(cache_key, config, fetch)
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    async def get_monthly_kline_async(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Async version of get_monthly_kline"""
        if start_date is None:
            start_date = "20200101"
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        config = CACHE_CONFIGS["monthly_kline"]
        cache_key = f"monthly:{code}:{start_date}:{end_date}:{adjust}"

        async def fetch() -> pd.DataFrame:
            return await run_akshare(
                StockDataFetcher.get_monthly_kline,
                code, start_date, end_date, adjust
            )

        result = await StockDataFetcher._cache.get(cache_key, config, fetch)
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

    @staticmethod
    async def get_realtime_quote_async(code: str) -> Optional[Dict[str, Any]]:
        """Async version of get_realtime_quote"""
        config = CACHE_CONFIGS["realtime_quote"]
        cache_key = code

        async def fetch() -> Optional[Dict[str, Any]]:
            return await run_akshare(StockDataFetcher.get_realtime_quote, code)

        return await StockDataFetcher._cache.get(cache_key, config, fetch)

    @staticmethod
    async def get_intraday_data_async(code: str) -> pd.DataFrame:
        """Async version of get_intraday_data"""
        config = CACHE_CONFIGS["intraday"]
        cache_key = code

        async def fetch() -> pd.DataFrame:
            return await run_akshare(StockDataFetcher.get_intraday_data, code)

        result = await StockDataFetcher._cache.get(cache_key, config, fetch)
        return result if isinstance(result, pd.DataFrame) else pd.DataFrame()

