"""Moving Average Crossover Strategy"""
import pandas as pd
from typing import Dict, Any, List
from .base_strategy import BaseStrategy, Signal


class MACrossStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy

    Buy when fast MA crosses above slow MA
    Sell when fast MA crosses below slow MA
    """

    name = "MA交叉策略"
    description = "快速均线上穿慢速均线时买入，下穿时卖出"

    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.fast_period = self.get_param("fast_period", 5)
        self.slow_period = self.get_param("slow_period", 20)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate moving averages"""
        df = df.copy()
        df['ma_fast'] = df['close'].rolling(window=self.fast_period).mean()
        df['ma_slow'] = df['close'].rolling(window=self.slow_period).mean()
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Generate crossover signals"""
        df = self.calculate_indicators(df)

        signals = pd.Series(Signal.HOLD, index=df.index)

        # Golden cross: fast MA crosses above slow MA
        golden_cross = (df['ma_fast'] > df['ma_slow']) & \
                      (df['ma_fast'].shift(1) <= df['ma_slow'].shift(1))

        # Death cross: fast MA crosses below slow MA
        death_cross = (df['ma_fast'] < df['ma_slow']) & \
                     (df['ma_fast'].shift(1) >= df['ma_slow'].shift(1))

        signals[golden_cross] = Signal.BUY
        signals[death_cross] = Signal.SELL

        return signals

    @classmethod
    def get_param_schema(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "fast_period",
                "type": "int",
                "default": 5,
                "min": 2,
                "max": 60,
                "description": "快速均线周期"
            },
            {
                "name": "slow_period",
                "type": "int",
                "default": 20,
                "min": 5,
                "max": 250,
                "description": "慢速均线周期"
            }
        ]


class DoubleMAStrategy(BaseStrategy):
    """
    Double Moving Average Strategy with trend filter

    Only buy when price is above long-term MA
    """

    name = "双均线趋势策略"
    description = "在长期均线上方时，快线上穿慢线买入；下穿卖出"

    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.fast_period = self.get_param("fast_period", 5)
        self.slow_period = self.get_param("slow_period", 20)
        self.trend_period = self.get_param("trend_period", 60)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['ma_fast'] = df['close'].rolling(window=self.fast_period).mean()
        df['ma_slow'] = df['close'].rolling(window=self.slow_period).mean()
        df['ma_trend'] = df['close'].rolling(window=self.trend_period).mean()
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = self.calculate_indicators(df)
        signals = pd.Series(Signal.HOLD, index=df.index)

        # Trend filter: price above long-term MA
        uptrend = df['close'] > df['ma_trend']

        # Crossover signals
        golden_cross = (df['ma_fast'] > df['ma_slow']) & \
                      (df['ma_fast'].shift(1) <= df['ma_slow'].shift(1))
        death_cross = (df['ma_fast'] < df['ma_slow']) & \
                     (df['ma_fast'].shift(1) >= df['ma_slow'].shift(1))

        # Only buy in uptrend
        signals[golden_cross & uptrend] = Signal.BUY
        signals[death_cross] = Signal.SELL

        return signals

    @classmethod
    def get_param_schema(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "fast_period", "type": "int", "default": 5, "min": 2, "max": 60, "description": "快速均线周期"},
            {"name": "slow_period", "type": "int", "default": 20, "min": 5, "max": 120, "description": "慢速均线周期"},
            {"name": "trend_period", "type": "int", "default": 60, "min": 20, "max": 250, "description": "趋势均线周期"}
        ]
