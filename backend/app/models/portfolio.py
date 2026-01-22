"""Portfolio database models"""
from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Portfolio(SQLModel, table=True):
    """Investment portfolio"""
    __tablename__ = "portfolios"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, description="Portfolio name")
    description: Optional[str] = Field(default=None, description="Description")
    initial_capital: float = Field(default=1000000, description="Initial capital")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Position(SQLModel, table=True):
    """Portfolio position"""
    __tablename__ = "positions"

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id", index=True)
    code: str = Field(max_length=10, description="Stock code")
    name: str = Field(max_length=50, description="Stock name")
    quantity: int = Field(description="Number of shares")
    avg_cost: float = Field(description="Average cost per share")
    buy_date: Optional[date] = Field(default=None, description="Buy date")
    notes: Optional[str] = Field(default=None, description="Notes")
    total_dividend: float = Field(default=0, description="Total dividend received")
    total_tax: float = Field(default=0, description="Total tax paid")
    created_at: datetime = Field(default_factory=datetime.now)


class Transaction(SQLModel, table=True):
    """Transaction record"""
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    portfolio_id: int = Field(foreign_key="portfolios.id", index=True)
    code: str = Field(max_length=10, description="Stock code")
    trade_type: str = Field(max_length=10, description="BUY/SELL/DIVIDEND/TAX")
    quantity: Optional[int] = Field(default=None, description="Number of shares (for BUY/SELL)")
    price: float = Field(description="Trade price or amount")
    commission: float = Field(default=0, description="Commission")
    trade_date: date = Field(description="Trade date")
    created_at: datetime = Field(default_factory=datetime.now)
