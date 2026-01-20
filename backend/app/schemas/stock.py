"""Stock API schemas"""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class StockInfo(BaseModel):
    """Stock basic information"""
    code: str
    name: str
    market: Optional[str] = None
    industry: Optional[str] = None


class KlineData(BaseModel):
    """Single K-line data point"""
    time: str  # Date string for frontend chart
    open: float
    high: float
    low: float
    close: float
    volume: float  # Volume in hands
    amount: Optional[float] = None  # 成交额
    turnover: Optional[float] = None  # 换手率


class KlineResponse(BaseModel):
    """K-line data response"""
    code: str
    name: str
    period: str
    data: List[KlineData]


class StockQuote(BaseModel):
    """Real-time stock quote"""
    code: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    pre_close: float
    volume: int
    amount: float
    time: str


class StockSearchResult(BaseModel):
    """Stock search result"""
    code: str
    name: str
    market: str


class IndicatorData(BaseModel):
    """Technical indicator data"""
    time: str
    value: float


class MAData(BaseModel):
    """Moving average data"""
    ma5: Optional[List[IndicatorData]] = None
    ma10: Optional[List[IndicatorData]] = None
    ma20: Optional[List[IndicatorData]] = None
    ma60: Optional[List[IndicatorData]] = None


class MACDData(BaseModel):
    """MACD indicator data"""
    macd: List[IndicatorData]
    signal: List[IndicatorData]
    histogram: List[IndicatorData]


class RSIData(BaseModel):
    """RSI indicator data"""
    rsi: List[IndicatorData]


class KDJData(BaseModel):
    """KDJ indicator data"""
    k: List[IndicatorData]
    d: List[IndicatorData]
    j: List[IndicatorData]


class BOLLData(BaseModel):
    """Bollinger Bands data"""
    upper: List[IndicatorData]
    middle: List[IndicatorData]
    lower: List[IndicatorData]


class IntradayData(BaseModel):
    """Intraday minute data point"""
    time: str  # Time string HH:MM
    price: float
    avg_price: float  # Average price (均价线)
    volume: float  # Volume in hands
    amount: float


class IntradayResponse(BaseModel):
    """Intraday data response"""
    code: str
    name: str
    pre_close: float  # Previous close for calculating change
    data: List[IntradayData]
