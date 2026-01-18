"""Performance metrics calculation"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any
from .strategies.base_strategy import Trade


class PerformanceMetrics:
    """Calculate backtest performance metrics"""

    @staticmethod
    def calculate_returns(equity_curve: List[float]) -> np.ndarray:
        """Calculate daily returns from equity curve"""
        equity = np.array(equity_curve)
        returns = np.diff(equity) / equity[:-1]
        return returns

    @staticmethod
    def total_return(initial: float, final: float) -> float:
        """Total return percentage"""
        return (final / initial - 1) * 100

    @staticmethod
    def annualized_return(total_return_pct: float, days: int) -> float:
        """Annualized return"""
        if days <= 0:
            return 0
        years = days / 252  # Trading days per year
        if years <= 0:
            return 0
        return ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100

    @staticmethod
    def max_drawdown(equity_curve: List[float]) -> Dict[str, float]:
        """
        Calculate maximum drawdown

        Returns:
            Dict with max_drawdown, max_drawdown_pct, peak_date_idx, trough_date_idx
        """
        equity = np.array(equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak

        max_dd_idx = np.argmin(drawdown)
        max_dd = drawdown[max_dd_idx]

        # Find peak before max drawdown
        peak_idx = np.argmax(equity[:max_dd_idx + 1]) if max_dd_idx > 0 else 0

        return {
            "max_drawdown": abs(max_dd) * 100,
            "peak_idx": int(peak_idx),
            "trough_idx": int(max_dd_idx),
            "peak_value": float(equity[peak_idx]),
            "trough_value": float(equity[max_dd_idx])
        }

    @staticmethod
    def sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.03) -> float:
        """
        Calculate Sharpe ratio

        Args:
            returns: Daily returns array
            risk_free_rate: Annual risk-free rate (default 3%)
        """
        if len(returns) == 0 or np.std(returns) == 0:
            return 0

        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf

        return np.sqrt(252) * np.mean(excess_returns) / np.std(returns)

    @staticmethod
    def sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0.03) -> float:
        """
        Calculate Sortino ratio (only considers downside volatility)
        """
        if len(returns) == 0:
            return 0

        daily_rf = risk_free_rate / 252
        excess_returns = returns - daily_rf

        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0

        return np.sqrt(252) * np.mean(excess_returns) / np.std(downside_returns)

    @staticmethod
    def calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio (return / max drawdown)"""
        if max_drawdown == 0:
            return 0
        return annualized_return / max_drawdown

    @staticmethod
    def win_rate(trades: List[Trade]) -> float:
        """Calculate win rate"""
        if not trades:
            return 0
        winning = sum(1 for t in trades if t.pnl > 0)
        return winning / len(trades) * 100

    @staticmethod
    def profit_factor(trades: List[Trade]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0
        return gross_profit / gross_loss

    @staticmethod
    def avg_trade_pnl(trades: List[Trade]) -> Dict[str, float]:
        """Calculate average trade statistics"""
        if not trades:
            return {"avg_pnl": 0, "avg_win": 0, "avg_loss": 0}

        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [t.pnl for t in trades if t.pnl < 0]

        return {
            "avg_pnl": sum(t.pnl for t in trades) / len(trades),
            "avg_win": sum(wins) / len(wins) if wins else 0,
            "avg_loss": sum(losses) / len(losses) if losses else 0,
            "avg_holding_days": sum(t.holding_days for t in trades) / len(trades)
        }

    @staticmethod
    def calculate_all(
        equity_curve: List[float],
        trades: List[Trade],
        initial_capital: float,
        trading_days: int
    ) -> Dict[str, Any]:
        """Calculate all performance metrics"""

        final_capital = equity_curve[-1] if equity_curve else initial_capital
        returns = PerformanceMetrics.calculate_returns(equity_curve)

        total_ret = PerformanceMetrics.total_return(initial_capital, final_capital)
        annual_ret = PerformanceMetrics.annualized_return(total_ret, trading_days)
        mdd = PerformanceMetrics.max_drawdown(equity_curve)
        sharpe = PerformanceMetrics.sharpe_ratio(returns)
        sortino = PerformanceMetrics.sortino_ratio(returns)
        calmar = PerformanceMetrics.calmar_ratio(annual_ret, mdd["max_drawdown"])
        win_rate = PerformanceMetrics.win_rate(trades)
        profit_fact = PerformanceMetrics.profit_factor(trades)
        trade_stats = PerformanceMetrics.avg_trade_pnl(trades)

        # Volatility
        volatility = np.std(returns) * np.sqrt(252) * 100 if len(returns) > 0 else 0

        return {
            "initial_capital": initial_capital,
            "final_capital": round(final_capital, 2),
            "total_return": round(total_ret, 2),
            "annualized_return": round(annual_ret, 2),
            "max_drawdown": round(mdd["max_drawdown"], 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "calmar_ratio": round(calmar, 2),
            "volatility": round(volatility, 2),
            "trade_count": len(trades),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_fact, 2) if profit_fact != float('inf') else 999.99,
            "avg_trade_pnl": round(trade_stats["avg_pnl"], 2),
            "avg_win": round(trade_stats["avg_win"], 2),
            "avg_loss": round(trade_stats["avg_loss"], 2),
            "avg_holding_days": round(trade_stats["avg_holding_days"], 1) if trades else 0,
            "trading_days": trading_days
        }
