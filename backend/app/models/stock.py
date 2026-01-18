"""Stock database models"""
from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Stock(SQLModel, table=True):
    """Stock basic information"""
    __tablename__ = "stocks"

    code: str = Field(primary_key=True, max_length=10, description="Stock code, e.g., 000001.SZ")
    name: str = Field(max_length=50, description="Stock name")
    market: Optional[str] = Field(default=None, max_length=10, description="Market: SH/SZ")
    industry: Optional[str] = Field(default=None, max_length=50, description="Industry")
    area: Optional[str] = Field(default=None, max_length=50, description="Region")
    list_date: Optional[date] = Field(default=None, description="Listing date")
    is_active: bool = Field(default=True, description="Is active")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")


class DailyKline(SQLModel, table=True):
    """Daily K-line data"""
    __tablename__ = "daily_kline"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, index=True, description="Stock code")
    trade_date: date = Field(index=True, description="Trade date")
    open: float = Field(description="Open price")
    high: float = Field(description="High price")
    low: float = Field(description="Low price")
    close: float = Field(description="Close price")
    pre_close: Optional[float] = Field(default=None, description="Previous close")
    change_pct: Optional[float] = Field(default=None, description="Change percentage")
    volume: int = Field(description="Volume (shares)")
    amount: float = Field(description="Amount (yuan)")
    turnover: Optional[float] = Field(default=None, description="Turnover rate")


class WeeklyKline(SQLModel, table=True):
    """Weekly K-line data"""
    __tablename__ = "weekly_kline"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, index=True)
    trade_date: date = Field(index=True)
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


class MonthlyKline(SQLModel, table=True):
    """Monthly K-line data"""
    __tablename__ = "monthly_kline"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, index=True)
    trade_date: date = Field(index=True)
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


class StockIndicator(SQLModel, table=True):
    """Technical indicator cache"""
    __tablename__ = "stock_indicators"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=10, index=True)
    trade_date: date = Field(index=True)
    indicator_type: str = Field(max_length=20, description="MA/MACD/RSI/KDJ/BOLL")
    params: str = Field(description="Parameters JSON")
    values: str = Field(description="Values JSON")
    created_at: datetime = Field(default_factory=datetime.now)
