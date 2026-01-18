"""Backtest Engine"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Type, Optional
from datetime import datetime

from .strategies.base_strategy import BaseStrategy, Signal, Position, Trade
from .strategies.ma_strategy import MACrossStrategy, DoubleMAStrategy
from .strategies.macd_strategy import MACDStrategy, MACDHistogramStrategy
from .strategies.oscillator_strategy import RSIStrategy, KDJStrategy, BollingerStrategy
from .metrics import PerformanceMetrics
from ..core.data_fetcher import StockDataFetcher


# Strategy registry
STRATEGIES: Dict[str, Type[BaseStrategy]] = {
    "ma_cross": MACrossStrategy,
    "double_ma": DoubleMAStrategy,
    "macd": MACDStrategy,
    "macd_hist": MACDHistogramStrategy,
    "rsi": RSIStrategy,
    "kdj": KDJStrategy,
    "bollinger": BollingerStrategy,
}


def get_strategy(name: str, params: Dict[str, Any] = None) -> BaseStrategy:
    """Get strategy instance by name"""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}")
    return STRATEGIES[name](params)


def get_available_strategies() -> List[Dict[str, Any]]:
    """Get list of available strategies with their parameters"""
    result = []
    for key, strategy_class in STRATEGIES.items():
        result.append({
            "id": key,
            "name": strategy_class.name,
            "description": strategy_class.description,
            "params": strategy_class.get_param_schema()
        })
    return result


class BacktestEngine:
    """
    Backtest Engine for running strategy simulations

    Features:
    - Single stock backtesting
    - Commission and slippage modeling
    - Position sizing
    - Trade tracking
    - Equity curve generation
    """

    def __init__(
        self,
        initial_capital: float = 1000000,
        commission: float = 0.0003,  # 0.03% per trade
        slippage: float = 0.001,     # 0.1% slippage
        position_size: float = 1.0,  # Use 100% of capital
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.position_size = position_size

        # State
        self.cash = initial_capital
        self.position = Position()
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict[str, Any]] = []

        # Trade tracking
        self._entry_date = None
        self._entry_price = None

    def reset(self):
        """Reset engine state"""
        self.cash = self.initial_capital
        self.position = Position()
        self.trades = []
        self.equity_curve = []
        self._entry_date = None
        self._entry_price = None

    def run(
        self,
        strategy: BaseStrategy,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Run backtest

        Args:
            strategy: Strategy instance
            df: DataFrame with OHLCV data (must have 'date', 'open', 'high', 'low', 'close', 'volume')

        Returns:
            Dict with backtest results
        """
        self.reset()

        # Generate signals
        signals = strategy.generate_signals(df)

        # Run simulation
        for i in range(len(df)):
            row = df.iloc[i]
            date = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], pd.Timestamp) else str(row['date'])
            close = row['close']
            signal = signals.iloc[i]

            # Process signal
            if signal == Signal.BUY and self.position.shares == 0:
                # Calculate position size
                available = self.cash * self.position_size
                price_with_slippage = close * (1 + self.slippage)
                shares = int(available / price_with_slippage / 100) * 100  # Round to 100 shares

                if shares >= 100:
                    cost = shares * price_with_slippage
                    commission = cost * self.commission

                    self.cash -= (cost + commission)
                    self.position.buy(shares, price_with_slippage)

                    self._entry_date = date
                    self._entry_price = price_with_slippage

            elif signal == Signal.SELL and self.position.shares > 0:
                # Sell all
                price_with_slippage = close * (1 - self.slippage)
                proceeds = self.position.shares * price_with_slippage
                commission = proceeds * self.commission

                # Record trade
                trade = Trade(
                    entry_date=self._entry_date,
                    entry_price=self._entry_price,
                    exit_date=date,
                    exit_price=price_with_slippage,
                    shares=self.position.shares
                )
                self.trades.append(trade)

                self.cash += (proceeds - commission)
                self.position = Position()
                self._entry_date = None
                self._entry_price = None

            # Record equity
            equity = self.cash + self.position.shares * close
            self.equity_curve.append({
                "date": date,
                "equity": round(equity, 2),
                "cash": round(self.cash, 2),
                "position_value": round(self.position.shares * close, 2),
                "close": close
            })

        # Close any open position at the end
        if self.position.shares > 0:
            last_row = df.iloc[-1]
            last_date = last_row['date'].strftime('%Y-%m-%d') if isinstance(last_row['date'], pd.Timestamp) else str(last_row['date'])
            last_close = last_row['close']

            trade = Trade(
                entry_date=self._entry_date,
                entry_price=self._entry_price,
                exit_date=last_date,
                exit_price=last_close,
                shares=self.position.shares
            )
            self.trades.append(trade)

        # Calculate metrics
        equity_values = [e["equity"] for e in self.equity_curve]
        metrics = PerformanceMetrics.calculate_all(
            equity_curve=equity_values,
            trades=self.trades,
            initial_capital=self.initial_capital,
            trading_days=len(df)
        )

        return {
            "metrics": metrics,
            "equity_curve": self.equity_curve,
            "trades": [t.to_dict() for t in self.trades]
        }


async def run_backtest(
    strategy_name: str,
    stock_code: str,
    params: Dict[str, Any] = None,
    start_date: str = None,
    end_date: str = None,
    initial_capital: float = 1000000,
    commission: float = 0.0003,
    slippage: float = 0.001
) -> Dict[str, Any]:
    """
    Run backtest for a single stock

    Args:
        strategy_name: Strategy ID
        stock_code: Stock code (e.g., 000001.SZ)
        params: Strategy parameters
        start_date: Start date (YYYYMMDD)
        end_date: End date (YYYYMMDD)
        initial_capital: Initial capital
        commission: Commission rate
        slippage: Slippage rate

    Returns:
        Backtest results
    """
    # Get strategy
    strategy = get_strategy(strategy_name, params)

    # Get data
    df = StockDataFetcher.get_daily_kline(
        stock_code,
        start_date=start_date,
        end_date=end_date
    )

    if df.empty:
        raise ValueError(f"No data found for {stock_code}")

    # Get stock info
    stock_info = StockDataFetcher.get_stock_info(stock_code)

    # Run backtest
    engine = BacktestEngine(
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage
    )

    result = engine.run(strategy, df)

    return {
        "stock": {
            "code": stock_code,
            "name": stock_info.get("name", "") if stock_info else ""
        },
        "strategy": {
            "id": strategy_name,
            "name": strategy.name,
            "params": params or {}
        },
        "period": {
            "start": df.iloc[0]['date'].strftime('%Y-%m-%d') if not df.empty else "",
            "end": df.iloc[-1]['date'].strftime('%Y-%m-%d') if not df.empty else ""
        },
        "config": {
            "initial_capital": initial_capital,
            "commission": commission,
            "slippage": slippage
        },
        **result
    }
