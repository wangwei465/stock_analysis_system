"""Fundamental data analyzer using AKShare"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd

from app.config import settings
from .async_utils import run_akshare
from .cache_manager import CacheManager, CacheConfig, CacheLevel

# 延迟导入 AKShare：避免在服务启动时引入重依赖导致冷启动变慢。
_ak = None

def get_akshare():
    """按需加载并缓存 AKShare 模块对象（`import akshare as ak` 的返回值）。"""
    global _ak
    if _ak is None:
        import akshare as ak
        _ak = ak
    return _ak

CACHE_CONFIGS = {
    "profile": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_fundamental),
        max_size=200,
        level=CacheLevel.BOTH,
        namespace="fundamental",
    ),
    "financial": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_fundamental),
        max_size=200,
        level=CacheLevel.BOTH,
        namespace="fundamental",
    ),
    "valuation": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_fundamental),
        max_size=200,
        level=CacheLevel.BOTH,
        namespace="fundamental",
    ),
    "dividend": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_fundamental),
        max_size=200,
        level=CacheLevel.BOTH,
        namespace="fundamental",
    ),
    "holders": CacheConfig(
        ttl=timedelta(seconds=settings.cache_ttl_fundamental),
        max_size=200,
        level=CacheLevel.BOTH,
        namespace="fundamental",
    ),
}


# ==================== Sync helper functions ====================
# These are the actual blocking operations that will be wrapped with run_akshare

def _get_company_profile_sync(symbol: str) -> Optional[pd.DataFrame]:
    """Sync function to get company profile"""
    try:
        ak = get_akshare()
        # AKShare: stock_individual_info_em 获取个股基本信息/公司概况，返回 item/value 结构的 DataFrame。
        # - symbol 为“纯数字股票代码”（不带 .SZ/.SH）
        return ak.stock_individual_info_em(symbol=symbol)
    except Exception as e:
        print(f"Error fetching profile for {symbol}: {e}")
        return None


def _get_financial_report_sync(symbol: str, report_type: str) -> Optional[pd.DataFrame]:
    """Sync function to get financial report"""
    try:
        ak = get_akshare()
        # AKShare: stock_financial_report_sina 通过 Sina 数据源拉取财务报表。
        # 该接口的报表类型参数使用中文名（利润表/资产负债表/现金流量表），因此这里做一次映射。
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
        # AKShare: stock_bid_ask_em 获取盘口/实时行情（item/value 结构），适合提取换手率、量比、振幅等实时指标。
        bid_ask_df = ak.stock_bid_ask_em(symbol=symbol)
        info_df = None
        try:
            # AKShare: stock_individual_info_em 作为补充数据源，用于补齐 PE/PB/市值等基本面字段。
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
        # AKShare: stock_history_dividend_detail 获取历史分红/送转等权益信息。
        # indicator='分红' 表示只取分红相关记录。
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
        # AKShare: stock_circulate_stock_holder 获取流通股东信息（包含季度、股东名称、持股数量等字段）。
        return ak.stock_circulate_stock_holder(symbol=symbol)
    except Exception as e:
        print(f"Error fetching top holders for {symbol}: {e}")
        return None


class FundamentalAnalyzer:
    """Fundamental data analyzer for A-share stocks"""

    _cache = CacheManager()

    @staticmethod
    async def get_company_profile(code: str) -> Optional[Dict[str, Any]]:
        """Get company profile information (async, non-blocking)"""
        config = CACHE_CONFIGS["profile"]
        cache_key = f"profile:{code}"

        symbol = code.split('.')[0]

        async def fetch() -> Optional[Dict[str, Any]]:
            df = await run_akshare(_get_company_profile_sync, symbol)
            if df is None or df.empty:
                return None

            profile = {}
            for _, row in df.iterrows():
                # stock_individual_info_em 返回为两列：item(指标名) / value(指标值)
                key = row['item']
                value = row['value']
                profile[key] = value

            return {
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

        return await FundamentalAnalyzer._cache.get(cache_key, config, fetch)

    @staticmethod
    async def get_financial_data(
        code: str,
        report_type: str = "income",
        limit: int = 8
    ) -> Optional[List[Dict[str, Any]]]:
        """Get financial statement data (async, non-blocking)"""
        config = CACHE_CONFIGS["financial"]
        cache_key = f"financial:{code}:{report_type}:{limit}"

        symbol = code.split('.')[0]

        async def fetch() -> Optional[List[Dict[str, Any]]]:
            df = await run_akshare(_get_financial_report_sync, symbol, report_type)
            if df is None or df.empty:
                return None
            df = df.head(limit)
            return df.to_dict('records')

        return await FundamentalAnalyzer._cache.get(cache_key, config, fetch)

    @staticmethod
    async def get_valuation(code: str) -> Optional[Dict[str, Any]]:
        """Get valuation metrics for a single stock (async, non-blocking)"""
        config = CACHE_CONFIGS["valuation"]
        cache_key = f"valuation:{code}"

        symbol = code.split('.')[0]

        async def fetch() -> Optional[Dict[str, Any]]:
            bid_ask_df, info_df = await run_akshare(_get_valuation_sync, symbol)
            if bid_ask_df is None or bid_ask_df.empty:
                return None

            # Convert to dict format (item-value structure)
            # stock_bid_ask_em 同样是 item/value 结构：把它转成 dict，便于按中文指标名取值。
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
                    # AKShare 的市值字段有时是带单位的字符串（例如：1234.56亿/789.01万）。
                    # 这里统一解析为“元”口径的数值，便于前端展示或后续计算。
                    if not val:
                        return None
                    try:
                        val_str = str(val).replace(',', '')
                        if '亿' in val_str:
                            return float(val_str.replace('亿', '')) * 100000000
                        if '万' in val_str:
                            return float(val_str.replace('万', '')) * 10000
                        return float(val_str)
                    except (ValueError, TypeError):
                        return None

                result['pe_ttm'] = safe_float(info_data.get('市盈率(动态)'))
                result['pb'] = safe_float(info_data.get('市净率'))
                result['market_cap'] = parse_market_cap(info_data.get('总市值'))
                result['circulating_cap'] = parse_market_cap(info_data.get('流通市值'))

            return result

        return await FundamentalAnalyzer._cache.get(cache_key, config, fetch)

    @staticmethod
    async def get_dividend_history(code: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get dividend history (async, non-blocking)"""
        config = CACHE_CONFIGS["dividend"]
        cache_key = f"dividend:{code}:{limit}"

        symbol = code.split('.')[0]

        async def fetch() -> Optional[List[Dict[str, Any]]]:
            df = await run_akshare(_get_dividend_history_sync, symbol)
            if df is None or df.empty:
                return []
            df = df.head(limit)
            return df.to_dict('records')

        return await FundamentalAnalyzer._cache.get(cache_key, config, fetch)

    @staticmethod
    async def get_top_holders(code: str) -> Optional[List[Dict[str, Any]]]:
        """Get top shareholders (async, non-blocking)"""
        config = CACHE_CONFIGS["holders"]
        cache_key = f"holders:{code}"

        symbol = code.split('.')[0]

        async def fetch() -> Optional[List[Dict[str, Any]]]:
            df = await run_akshare(_get_top_holders_sync, symbol)
            if df is None or df.empty:
                return []

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
            return result

        return await FundamentalAnalyzer._cache.get(cache_key, config, fetch)
