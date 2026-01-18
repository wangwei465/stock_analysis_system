"""Stock data fetcher using AKShare"""
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
from functools import lru_cache
from cachetools import TTLCache

from .async_utils import run_sync

# Lazy import AKShare to avoid slow startup
_ak = None

def get_akshare():
    """Lazy load akshare module"""
    global _ak
    if _ak is None:
        import akshare as ak
        _ak = ak
    return _ak

# Cache for stock list (1 hour TTL)
_stock_list_cache = TTLCache(maxsize=1, ttl=3600)


class StockDataFetcher:
    """A-share stock data fetcher using AKShare"""

    @staticmethod
    def get_stock_list() -> pd.DataFrame:
        """Get A-share stock list"""
        cache_key = "stock_list"
        if cache_key in _stock_list_cache:
            return _stock_list_cache[cache_key]

        try:
            ak = get_akshare()
            df = ak.stock_info_a_code_name()
            # Add market suffix
            df['market'] = df['code'].apply(
                lambda x: 'SH' if x.startswith('6') else 'SZ'
            )
            df['full_code'] = df.apply(
                lambda row: f"{row['code']}.{'SH' if row['code'].startswith('6') else 'SZ'}",
                axis=1
            )
            _stock_list_cache[cache_key] = df
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
            # 按需获取单只股票数据（替代 stock_zh_a_spot_em 全量获取）
            df = ak.stock_bid_ask_em(symbol=symbol)

            if df.empty:
                return None

            # 转换为字典格式 (item-value 结构)
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
                'volume': safe_int(data.get('总手')),  # 修正字段名：总手（单位：手）
                'amount': safe_float(data.get('金额')),  # 修正字段名：金额（单位：元）
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
        # Convert to sina format: sh600000 or sz000001
        if symbol.startswith('6'):
            sina_symbol = f'sh{symbol}'
        else:
            sina_symbol = f'sz{symbol}'

        try:
            ak = get_akshare()
            # Get 1-minute data
            df = ak.stock_zh_a_minute(symbol=sina_symbol, period='1', adjust='')

            if df.empty:
                return pd.DataFrame()

            # Rename columns - API returns 'day' not 'time'
            df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']

            # Parse time - the format is like "2024-01-17 09:31:00"
            df['time'] = pd.to_datetime(df['time'])

            # Filter to get the latest trading day's data (not necessarily today)
            # This handles weekends and holidays correctly
            if len(df) > 0:
                latest_date = df['time'].dt.date.max()
                df = df[df['time'].dt.date == latest_date]

            # Convert numeric columns
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
        return await run_sync(StockDataFetcher.get_stock_list)

    @staticmethod
    async def search_stocks_async(keyword: str, limit: int = 20) -> List[Dict[str, str]]:
        """Async version of search_stocks"""
        return await run_sync(StockDataFetcher.search_stocks, keyword, limit)

    @staticmethod
    async def get_stock_info_async(code: str) -> Optional[Dict[str, Any]]:
        """Async version of get_stock_info"""
        return await run_sync(StockDataFetcher.get_stock_info, code)

    @staticmethod
    async def get_daily_kline_async(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Async version of get_daily_kline"""
        return await run_sync(
            StockDataFetcher.get_daily_kline,
            code, start_date, end_date, adjust
        )

    @staticmethod
    async def get_weekly_kline_async(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Async version of get_weekly_kline"""
        return await run_sync(
            StockDataFetcher.get_weekly_kline,
            code, start_date, end_date, adjust
        )

    @staticmethod
    async def get_monthly_kline_async(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """Async version of get_monthly_kline"""
        return await run_sync(
            StockDataFetcher.get_monthly_kline,
            code, start_date, end_date, adjust
        )

    @staticmethod
    async def get_realtime_quote_async(code: str) -> Optional[Dict[str, Any]]:
        """Async version of get_realtime_quote"""
        return await run_sync(StockDataFetcher.get_realtime_quote, code)

    @staticmethod
    async def get_intraday_data_async(code: str) -> pd.DataFrame:
        """Async version of get_intraday_data"""
        return await run_sync(StockDataFetcher.get_intraday_data, code)

