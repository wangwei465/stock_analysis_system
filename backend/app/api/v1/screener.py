"""Stock screener API endpoints"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.core.stock_screener import StockScreener

router = APIRouter()


class ScreenerCondition(BaseModel):
    """Single screening condition"""
    field: str
    operator: str  # gt, gte, lt, lte, eq, between, in
    value: float | List[float] | List[str]


class ScreenerRequest(BaseModel):
    """Screener request body"""
    conditions: List[ScreenerCondition]
    sort_by: Optional[str] = "market_cap"
    sort_order: Optional[str] = "desc"
    page: Optional[int] = 1
    page_size: Optional[int] = 50
    market_boards: Optional[List[str]] = None  # 包含的板块
    exclude_boards: Optional[List[str]] = None  # 排除的板块


@router.post("/filter")
async def filter_stocks(request: ScreenerRequest):
    """
    Filter stocks by multiple conditions

    Supported fields:
    - price: Current price
    - change_pct: Change percentage
    - pe: PE ratio (TTM)
    - pb: PB ratio
    - market_cap: Market cap (in 100 million)
    - turnover_rate: Turnover rate
    - volume_ratio: Volume ratio
    - amplitude: Amplitude

    Operators:
    - gt: Greater than
    - gte: Greater than or equal
    - lt: Less than
    - lte: Less than or equal
    - eq: Equal
    - between: Between two values [min, max]
    - in: In list of values

    Market boards:
    - sh_main: 沪市主板 (60开头)
    - sz_main: 深市主板 (000、001开头)
    - gem: 创业板 (30开头)
    - star: 科创板 (688开头)
    - bse: 北交所 (8开头)
    """
    try:
        results = await StockScreener.filter_stocks(
            conditions=[c.model_dump() for c in request.conditions],
            sort_by=request.sort_by,
            sort_order=request.sort_order,
            page=request.page,
            page_size=request.page_size,
            market_boards=request.market_boards,
            exclude_boards=request.exclude_boards
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/presets")
async def get_presets():
    """Get preset screening conditions"""
    return [
        {
            "name": "低估值蓝筹",
            "description": "PE < 15, PB < 2, 市值 > 500亿",
            "conditions": [
                {"field": "pe", "operator": "lt", "value": 15},
                {"field": "pb", "operator": "lt", "value": 2},
                {"field": "market_cap", "operator": "gt", "value": 500},
            ],
            "market_boards": ["sh_main", "sz_main"],
            "exclude_boards": []
        },
        {
            "name": "小盘成长",
            "description": "市值 < 100亿, 换手率 > 3%",
            "conditions": [
                {"field": "market_cap", "operator": "lt", "value": 100},
                {"field": "turnover_rate", "operator": "gt", "value": 3},
            ],
            "market_boards": [],
            "exclude_boards": []
        },
        {
            "name": "强势股",
            "description": "涨幅 > 5%, 量比 > 2",
            "conditions": [
                {"field": "change_pct", "operator": "gt", "value": 5},
                {"field": "volume_ratio", "operator": "gt", "value": 2},
            ],
            "market_boards": [],
            "exclude_boards": []
        },
        {
            "name": "超跌反弹",
            "description": "跌幅 > 5%, 换手率 > 5%",
            "conditions": [
                {"field": "change_pct", "operator": "lt", "value": -5},
                {"field": "turnover_rate", "operator": "gt", "value": 5},
            ],
            "market_boards": [],
            "exclude_boards": []
        },
        {
            "name": "高股息",
            "description": "PE < 20, PB < 3, 市值 > 100亿",
            "conditions": [
                {"field": "pe", "operator": "lt", "value": 20},
                {"field": "pb", "operator": "lt", "value": 3},
                {"field": "market_cap", "operator": "gt", "value": 100},
            ],
            "market_boards": [],
            "exclude_boards": []
        },
        {
            "name": "主板价值股",
            "description": "沪深主板, PE < 20, 市值 > 200亿",
            "conditions": [
                {"field": "pe", "operator": "lt", "value": 20},
                {"field": "market_cap", "operator": "gt", "value": 200},
            ],
            "market_boards": ["sh_main", "sz_main"],
            "exclude_boards": []
        },
        {
            "name": "创业板活跃股",
            "description": "创业板, 换手率 > 5%, 量比 > 1.5",
            "conditions": [
                {"field": "turnover_rate", "operator": "gt", "value": 5},
                {"field": "volume_ratio", "operator": "gt", "value": 1.5},
            ],
            "market_boards": ["gem"],
            "exclude_boards": []
        },
        {
            "name": "科创板",
            "description": "科创板全部股票",
            "conditions": [],
            "market_boards": ["star"],
            "exclude_boards": []
        }
    ]


@router.get("/fields")
async def get_available_fields():
    """Get available screening fields"""
    return [
        {"field": "price", "name": "现价", "type": "number", "unit": "元"},
        {"field": "change_pct", "name": "涨跌幅", "type": "number", "unit": "%"},
        {"field": "pe", "name": "市盈率(TTM)", "type": "number", "unit": ""},
        {"field": "pb", "name": "市净率", "type": "number", "unit": ""},
        {"field": "market_cap", "name": "总市值", "type": "number", "unit": "亿元"},
        {"field": "circulating_cap", "name": "流通市值", "type": "number", "unit": "亿元"},
        {"field": "turnover_rate", "name": "换手率", "type": "number", "unit": "%"},
        {"field": "volume_ratio", "name": "量比", "type": "number", "unit": ""},
        {"field": "amplitude", "name": "振幅", "type": "number", "unit": "%"},
    ]


@router.get("/boards")
async def get_market_boards():
    """Get available market boards for filtering"""
    return StockScreener.get_available_boards()
