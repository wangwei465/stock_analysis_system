"""Fundamental data analyzer using AKShare"""
import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import datetime
from cachetools import TTLCache

from .async_utils import run_sync

# Lazy import AKShare
_ak = None

def get_akshare():
    global _ak
    if _ak is None:
        import akshare as ak
        _ak = ak
    return _ak

# Cache for fundamental data (30 minutes TTL)
_fundamental_cache = TTLCache(maxsize=100, ttl=1800)


# ==================== Sync helper functions ====================
# These are the actual blocking operations that will be wrapped with run_sync

def _get_company_profile_sync(symbol: str) -> Optional[pd.DataFrame]:
    """Sync function to get company profile"""
    try:
        ak = get_akshare()
        return ak.stock_individual_info_em(symbol=symbol)
    except Exception as e:
        print(f"Error fetching profile for {symbol}: {e}")
        return None


def _get_financial_report_sync(symbol: str, report_type: str) -> Optional[pd.DataFrame]:
    """Sync function to get financial report"""
    try:
        ak = get_akshare()
        symbol_map = {
            "income": "利润表",
            "balance": "资产负债表",
            "cashflow": "现金流量表"
        }
        return ak.stock_financial_report_sina(
            stock=symbol,
            symbol=symbol_map.get(report_type, "利润表")
        )
    except Exception as e:
        print(f"Error fetching financial data for {symbol}: {e}")
        return None


def _get_valuation_sync(symbol: str) -> tuple:
    """Sync function to get valuation data (returns bid_ask_df and info_df)"""
    try:
        ak = get_akshare()
        bid_ask_df = ak.stock_bid_ask_em(symbol=symbol)
        info_df = None
        try:
            info_df = ak.stock_individual_info_em(symbol=symbol)
        except Exception:
            pass
        return bid_ask_df, info_df
    except Exception as e:
        print(f"Error fetching valuation for {symbol}: {e}")
        return None, None


def _get_dividend_history_sync(symbol: str) -> Optional[pd.DataFrame]:
    """Sync function to get dividend history"""
    try:
        ak = get_akshare()
        return ak.stock_history_dividend_detail(
            symbol=symbol,
            indicator="分红"
        )
    except Exception as e:
        print(f"Error fetching dividend history for {symbol}: {e}")
        return None


def _get_top_holders_sync(symbol: str) -> Optional[pd.DataFrame]:
    """Sync function to get top shareholders"""
    try:
        ak = get_akshare()
        return ak.stock_circulate_stock_holder(symbol=symbol)
    except Exception as e:
        print(f"Error fetching top holders for {symbol}: {e}")
        return None


class FundamentalAnalyzer:
    """Fundamental data analyzer for A-share stocks"""

    @staticmethod
    async def get_company_profile(code: str) -> Optional[Dict[str, Any]]:
        """Get company profile information (async, non-blocking)"""
        cache_key = f"profile_{code}"
        if cache_key in _fundamental_cache:
            return _fundamental_cache[cache_key]

        symbol = code.split('.')[0]

        # Use run_sync to avoid blocking
        df = await run_sync(_get_company_profile_sync, symbol)

        if df is None or df.empty:
            return None

        # Convert to dict
        profile = {}
        for _, row in df.iterrows():
            key = row['item']
            value = row['value']
            profile[key] = value

        result = {
            'code': code,
            'name': profile.get('股票简称', ''),
            'industry': profile.get('行业', ''),
            'market_cap': profile.get('总市值', ''),
            'circulating_cap': profile.get('流通市值', ''),
            'total_shares': profile.get('总股本', ''),
            'circulating_shares': profile.get('流通股', ''),
            'pe_ttm': profile.get('市盈率(动态)', ''),
            'pb': profile.get('市净率', ''),
            'list_date': profile.get('上市时间', ''),
        }

        _fundamental_cache[cache_key] = result
        return result

    @staticmethod
    async def get_financial_data(
        code: str,
        report_type: str = "income",
        limit: int = 8
    ) -> Optional[List[Dict[str, Any]]]:
        """Get financial statement data (async, non-blocking)"""
        cache_key = f"financial_{code}_{report_type}"
        if cache_key in _fundamental_cache:
            return _fundamental_cache[cache_key]

        symbol = code.split('.')[0]

        # Use run_sync to avoid blocking
        df = await run_sync(_get_financial_report_sync, symbol, report_type)

        if df is None or df.empty:
            return None

        # Take recent reports
        df = df.head(limit)

        # Convert to list of dicts
        result = df.to_dict('records')

        _fundamental_cache[cache_key] = result
        return result

    @staticmethod
    async def get_valuation(code: str) -> Optional[Dict[str, Any]]:
        """Get valuation metrics for a single stock (async, non-blocking)"""
        cache_key = f"valuation_{code}"
        if cache_key in _fundamental_cache:
            return _fundamental_cache[cache_key]

        symbol = code.split('.')[0]

        # Use run_sync to avoid blocking
        bid_ask_df, info_df = await run_sync(_get_valuation_sync, symbol)

        if bid_ask_df is None or bid_ask_df.empty:
            return None

        # Convert to dict format (item-value structure)
        data = dict(zip(bid_ask_df['item'], bid_ask_df['value']))

        def safe_float(val, default=None):
            try:
                return float(val) if val else default
            except (ValueError, TypeError):
                return default

        result = {
            'code': code,
            'name': data.get('名称', ''),
            'price': safe_float(data.get('最新')),
            'pe_ttm': None,
            'pb': None,
            'market_cap': None,
            'circulating_cap': None,
            'turnover_rate': safe_float(data.get('换手')),
            'volume_ratio': safe_float(data.get('量比')),
            'amplitude': safe_float(data.get('振幅')),
            '52w_high': None,
            '52w_low': None,
        }

        # Supplement with PE/PB/market cap from info_df
        if info_df is not None and not info_df.empty:
            info_data = dict(zip(info_df['item'], info_df['value']))

            def parse_market_cap(val):
                """Parse market cap string like '1234.56亿' -> 123456000000"""
                if not val:
                    return None
                try:
                    val_str = str(val).replace(',', '')
                    if '亿' in val_str:
                        return float(val_str.replace('亿', '')) * 100000000
                    elif '万' in val_str:
                        return float(val_str.replace('万', '')) * 10000
                    return float(val_str)
                except (ValueError, TypeError):
                    return None

            result['pe_ttm'] = safe_float(info_data.get('市盈率(动态)'))
            result['pb'] = safe_float(info_data.get('市净率'))
            result['market_cap'] = parse_market_cap(info_data.get('总市值'))
            result['circulating_cap'] = parse_market_cap(info_data.get('流通市值'))

        _fundamental_cache[cache_key] = result
        return result

    @staticmethod
    async def get_dividend_history(code: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get dividend history (async, non-blocking)"""
        cache_key = f"dividend_{code}"
        if cache_key in _fundamental_cache:
            return _fundamental_cache[cache_key]

        symbol = code.split('.')[0]

        # Use run_sync to avoid blocking
        df = await run_sync(_get_dividend_history_sync, symbol)

        if df is None or df.empty:
            return []

        df = df.head(limit)
        result = df.to_dict('records')

        _fundamental_cache[cache_key] = result
        return result

    @staticmethod
    async def get_top_holders(code: str) -> Optional[List[Dict[str, Any]]]:
        """Get top shareholders (async, non-blocking)"""
        cache_key = f"holders_{code}"
        if cache_key in _fundamental_cache:
            return _fundamental_cache[cache_key]

        symbol = code.split('.')[0]

        # Use run_sync to avoid blocking
        df = await run_sync(_get_top_holders_sync, symbol)

        if df is None or df.empty:
            return []

        # Get latest report
        latest_date = df['季度'].max()
        df = df[df['季度'] == latest_date]

        result = []
        for _, row in df.iterrows():
            result.append({
                'report_date': row['季度'],
                'holder_name': row['股东名称'],
                'holder_type': row['股东性质'] if '股东性质' in row else '',
                'shares': row['持股数量'] if '持股数量' in row else 0,
                'ratio': row['占流通股比例'] if '占流通股比例' in row else 0,
                'change': row['增减'] if '增减' in row else '',
            })

        _fundamental_cache[cache_key] = result
        return result
