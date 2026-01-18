"""Base strategy class for backtesting"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd


class Signal:
    """Trading signal"""
    BUY = 1
    SELL = -1
    HOLD = 0


class Position:
    """Position tracker"""

    def __init__(self):
        self.shares = 0
        self.avg_cost = 0.0
        self.total_cost = 0.0

    def buy(self, shares: int, price: float):
        """Add to position"""
        cost = shares * price
        self.total_cost += cost
        self.shares += shares
        self.avg_cost = self.total_cost / self.shares if self.shares > 0 else 0

    def sell(self, shares: int, price: float) -> float:
        """Reduce position, return realized PnL"""
        if shares > self.shares:
            shares = self.shares

        pnl = shares * (price - self.avg_cost)
        self.shares -= shares
        self.total_cost = self.shares * self.avg_cost

        if self.shares == 0:
            self.avg_cost = 0
            self.total_cost = 0

        return pnl

    def sell_all(self, price: float) -> float:
        """Sell all shares"""
        return self.sell(self.shares, price)

    @property
    def market_value(self) -> float:
        """Current market value (needs current price)"""
        return 0  # Will be calculated externally


class BaseStrategy(ABC):
    """Abstract base class for trading strategies"""

    name: str = "Base Strategy"
    description: str = "Base strategy class"

    def __init__(self, params: Dict[str, Any] = None):
        self.params = params or {}
        self._indicators = {}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals for each bar

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Series with signal values (1=buy, -1=sell, 0=hold)
        """
        pass

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators needed for the strategy.
        Override in subclass if needed.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with additional indicator columns
        """
        return df

    def get_param(self, key: str, default: Any = None) -> Any:
        """Get parameter value"""
        return self.params.get(key, default)

    @classmethod
    def get_param_schema(cls) -> List[Dict[str, Any]]:
        """
        Return parameter schema for UI

        Returns:
            List of param definitions: [{name, type, default, min, max, description}]
        """
        return []


class Trade:
    """Represents a completed trade"""

    def __init__(
        self,
        entry_date: str,
        entry_price: float,
        exit_date: str,
        exit_price: float,
        shares: int,
        direction: str = "LONG"
    ):
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.shares = shares
        self.direction = direction

    @property
    def pnl(self) -> float:
        """Profit/Loss"""
        if self.direction == "LONG":
            return (self.exit_price - self.entry_price) * self.shares
        else:
            return (self.entry_price - self.exit_price) * self.shares

    @property
    def pnl_pct(self) -> float:
        """PnL percentage"""
        return (self.exit_price / self.entry_price - 1) * 100

    @property
    def holding_days(self) -> int:
        """Number of days held"""
        from datetime import datetime
        entry = datetime.strptime(self.entry_date, "%Y-%m-%d")
        exit = datetime.strptime(self.exit_date, "%Y-%m-%d")
        return (exit - entry).days

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_date": self.entry_date,
            "entry_price": self.entry_price,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "shares": self.shares,
            "direction": self.direction,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "holding_days": self.holding_days
        }
