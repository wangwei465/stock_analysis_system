"""Stock screener core logic"""
import pandas as pd
from typing import List, Dict, Any, Optional
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


def _fetch_all_stocks_sync() -> pd.DataFrame:
    """Sync function to fetch all stocks data (to be wrapped with run_sync)"""
    try:
        ak = get_akshare()
        df = ak.stock_zh_a_spot_em()

        if df.empty:
            return pd.DataFrame()

        # Convert market cap to 100 million
        if '总市值' in df.columns:
            df['总市值'] = df['总市值'] / 100000000
        if '流通市值' in df.columns:
            df['流通市值'] = df['流通市值'] / 100000000

        return df
    except Exception as e:
        print(f"Error fetching all stocks data: {e}")
        return pd.DataFrame()


# Cache for stock data (5 minutes TTL)
_stock_data_cache = TTLCache(maxsize=1, ttl=300)


# 板块定义
MARKET_BOARDS = {
    'sh_main': {
        'name': '沪市主板',
        'description': '上海证券交易所主板（60开头）',
        'pattern': lambda code: code.startswith('60')
    },
    'sz_main': {
        'name': '深市主板',
        'description': '深圳证券交易所主板（000、001开头）',
        'pattern': lambda code: code.startswith('000') or code.startswith('001')
    },
    'gem': {
        'name': '创业板',
        'description': '深圳创业板（30开头）',
        'pattern': lambda code: code.startswith('30')
    },
    'star': {
        'name': '科创板',
        'description': '上海科创板（688开头）',
        'pattern': lambda code: code.startswith('688')
    },
    'bse': {
        'name': '北交所',
        'description': '北京证券交易所（8开头）',
        'pattern': lambda code: code.startswith('8')
    }
}


class StockScreener:
    """Stock screening engine"""

    # Field mapping: API field -> DataFrame column
    FIELD_MAPPING = {
        'price': '最新价',
        'change_pct': '涨跌幅',
        'pe': '市盈率-动态',
        'pb': '市净率',
        'market_cap': '总市值',
        'circulating_cap': '流通市值',
        'turnover_rate': '换手率',
        'volume_ratio': '量比',
        'amplitude': '振幅',
    }

    @classmethod
    async def get_all_stocks_data(cls) -> pd.DataFrame:
        """Get all A-share stocks data (async, non-blocking)"""
        cache_key = "all_stocks"
        if cache_key in _stock_data_cache:
            return _stock_data_cache[cache_key]

        # Use run_sync to avoid blocking the event loop
        df = await run_sync(_fetch_all_stocks_sync)

        if not df.empty:
            _stock_data_cache[cache_key] = df

        return df

    @classmethod
    def apply_condition(cls, df: pd.DataFrame, condition: Dict[str, Any]) -> pd.DataFrame:
        """Apply a single filter condition"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')

        if field not in cls.FIELD_MAPPING:
            return df

        column = cls.FIELD_MAPPING[field]
        if column not in df.columns:
            return df

        # Convert column to numeric
        df[column] = pd.to_numeric(df[column], errors='coerce')

        if operator == 'gt':
            return df[df[column] > value]
        elif operator == 'gte':
            return df[df[column] >= value]
        elif operator == 'lt':
            return df[df[column] < value]
        elif operator == 'lte':
            return df[df[column] <= value]
        elif operator == 'eq':
            return df[df[column] == value]
        elif operator == 'between':
            if isinstance(value, list) and len(value) == 2:
                return df[(df[column] >= value[0]) & (df[column] <= value[1])]
        elif operator == 'in':
            if isinstance(value, list):
                return df[df[column].isin(value)]

        return df

    @classmethod
    async def filter_stocks(
        cls,
        conditions: List[Dict[str, Any]],
        sort_by: Optional[str] = "market_cap",
        sort_order: Optional[str] = "desc",
        page: int = 1,
        page_size: int = 50,
        market_boards: Optional[List[str]] = None,
        exclude_boards: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Filter stocks by multiple conditions

        Args:
            conditions: List of filter conditions
            sort_by: Sort field
            sort_order: Sort order ('asc' or 'desc')
            page: Page number
            page_size: Items per page
            market_boards: List of market boards to include (e.g., ['sh_main', 'sz_main'])
            exclude_boards: List of market boards to exclude (e.g., ['star', 'gem'])

        Returns:
            Dict with 'total', 'page', 'page_size', 'data'
        """
        df = await cls.get_all_stocks_data()

        if df.empty:
            return {"total": 0, "page": page, "page_size": page_size, "data": []}

        # Apply market board filter
        if market_boards or exclude_boards:
            df = cls.apply_market_board_filter(df, market_boards, exclude_boards)

        # Apply all conditions
        for condition in conditions:
            df = cls.apply_condition(df, condition)

        # Get total count after filtering
        total = len(df)

        # Sort
        if sort_by and sort_by in cls.FIELD_MAPPING:
            sort_column = cls.FIELD_MAPPING[sort_by]
            if sort_column in df.columns:
                df = df.sort_values(
                    by=sort_column,
                    ascending=(sort_order == 'asc'),
                    na_position='last'
                )

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        df = df.iloc[start:end]

        # Convert to response format
        results = []
        for _, row in df.iterrows():
            code = str(row['代码'])
            market = 'SH' if code.startswith('6') else 'SZ'
            board = cls.get_stock_board(code)
            results.append({
                'code': f"{code}.{market}",
                'name': row['名称'],
                'board': board,
                'price': float(row['最新价']) if pd.notna(row['最新价']) else None,
                'change_pct': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else None,
                'pe': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
                'pb': float(row['市净率']) if pd.notna(row['市净率']) else None,
                'market_cap': round(float(row['总市值']), 2) if pd.notna(row['总市值']) else None,
                'circulating_cap': round(float(row['流通市值']), 2) if pd.notna(row['流通市值']) else None,
                'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else None,
                'volume_ratio': float(row['量比']) if pd.notna(row['量比']) else None,
                'amplitude': float(row['振幅']) if pd.notna(row['振幅']) else None,
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "data": results
        }

    @classmethod
    def apply_market_board_filter(
        cls,
        df: pd.DataFrame,
        include_boards: Optional[List[str]] = None,
        exclude_boards: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Filter stocks by market board

        Args:
            df: DataFrame with stock data
            include_boards: List of boards to include
            exclude_boards: List of boards to exclude

        Returns:
            Filtered DataFrame
        """
        if df.empty:
            return df

        # Convert code column to string
        df['代码'] = df['代码'].astype(str)

        # Build include mask
        if include_boards:
            include_mask = pd.Series([False] * len(df), index=df.index)
            for board in include_boards:
                if board in MARKET_BOARDS:
                    pattern_func = MARKET_BOARDS[board]['pattern']
                    include_mask = include_mask | df['代码'].apply(pattern_func)
            df = df[include_mask]

        # Build exclude mask
        if exclude_boards:
            exclude_mask = pd.Series([False] * len(df), index=df.index)
            for board in exclude_boards:
                if board in MARKET_BOARDS:
                    pattern_func = MARKET_BOARDS[board]['pattern']
                    exclude_mask = exclude_mask | df['代码'].apply(pattern_func)
            df = df[~exclude_mask]

        return df

    @classmethod
    def get_stock_board(cls, code: str) -> str:
        """Get the market board name for a stock code"""
        code = str(code)
        for board_key, board_info in MARKET_BOARDS.items():
            if board_info['pattern'](code):
                return board_info['name']
        return '其他'

    @classmethod
    def get_available_boards(cls) -> List[Dict[str, str]]:
        """Get list of available market boards"""
        return [
            {'key': key, 'name': info['name'], 'description': info['description']}
            for key, info in MARKET_BOARDS.items()
        ]
