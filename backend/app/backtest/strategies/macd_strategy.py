"""MACD Strategy"""
import pandas as pd
from typing import Dict, Any, List
from .base_strategy import BaseStrategy, Signal


class MACDStrategy(BaseStrategy):
    """
    MACD Strategy

    Buy when MACD crosses above signal line
    Sell when MACD crosses below signal line
    """

    name = "MACD策略"
    description = "MACD金叉买入，死叉卖出"

    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.fast_period = self.get_param("fast_period", 12)
        self.slow_period = self.get_param("slow_period", 26)
        self.signal_period = self.get_param("signal_period", 9)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # Calculate MACD
        exp1 = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.slow_period, adjust=False).mean()

        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = self.calculate_indicators(df)
        signals = pd.Series(Signal.HOLD, index=df.index)

        # Golden cross: MACD crosses above signal
        golden_cross = (df['macd'] > df['macd_signal']) & \
                      (df['macd'].shift(1) <= df['macd_signal'].shift(1))

        # Death cross: MACD crosses below signal
        death_cross = (df['macd'] < df['macd_signal']) & \
                     (df['macd'].shift(1) >= df['macd_signal'].shift(1))

        signals[golden_cross] = Signal.BUY
        signals[death_cross] = Signal.SELL

        return signals

    @classmethod
    def get_param_schema(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "fast_period", "type": "int", "default": 12, "min": 5, "max": 50, "description": "快线周期"},
            {"name": "slow_period", "type": "int", "default": 26, "min": 10, "max": 100, "description": "慢线周期"},
            {"name": "signal_period", "type": "int", "default": 9, "min": 3, "max": 30, "description": "信号线周期"}
        ]


class MACDHistogramStrategy(BaseStrategy):
    """
    MACD Histogram Strategy

    Buy when histogram turns from negative to positive
    Sell when histogram turns from positive to negative
    """

    name = "MACD柱状图策略"
    description = "MACD柱状图由负转正买入，由正转负卖出"

    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.fast_period = self.get_param("fast_period", 12)
        self.slow_period = self.get_param("slow_period", 26)
        self.signal_period = self.get_param("signal_period", 9)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        exp1 = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.signal_period, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = self.calculate_indicators(df)
        signals = pd.Series(Signal.HOLD, index=df.index)

        # Histogram turns positive
        buy_signal = (df['macd_hist'] > 0) & (df['macd_hist'].shift(1) <= 0)
        # Histogram turns negative
        sell_signal = (df['macd_hist'] < 0) & (df['macd_hist'].shift(1) >= 0)

        signals[buy_signal] = Signal.BUY
        signals[sell_signal] = Signal.SELL

        return signals

    @classmethod
    def get_param_schema(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "fast_period", "type": "int", "default": 12, "min": 5, "max": 50, "description": "快线周期"},
            {"name": "slow_period", "type": "int", "default": 26, "min": 10, "max": 100, "description": "慢线周期"},
            {"name": "signal_period", "type": "int", "default": 9, "min": 3, "max": 30, "description": "信号线周期"}
        ]
