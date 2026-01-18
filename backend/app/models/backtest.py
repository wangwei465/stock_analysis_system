"""Backtest result database model"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class BacktestResult(SQLModel, table=True):
    """Backtest result storage"""
    __tablename__ = "backtest_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_name: str = Field(max_length=50, description="Strategy ID")
    strategy_display_name: str = Field(max_length=100, description="Strategy display name")
    params: str = Field(description="Strategy parameters JSON")
    stock_code: str = Field(max_length=10, description="Stock code")
    stock_name: str = Field(max_length=50, description="Stock name")
    start_date: str = Field(max_length=10, description="Backtest start date")
    end_date: str = Field(max_length=10, description="Backtest end date")
    initial_capital: float = Field(description="Initial capital")
    final_capital: float = Field(description="Final capital")
    total_return: float = Field(description="Total return %")
    annualized_return: float = Field(description="Annualized return %")
    max_drawdown: float = Field(description="Max drawdown %")
    sharpe_ratio: float = Field(description="Sharpe ratio")
    win_rate: float = Field(description="Win rate %")
    trade_count: int = Field(description="Number of trades")
    result_detail: str = Field(description="Full result JSON")
    created_at: datetime = Field(default_factory=datetime.now)
