"""RSI and KDJ Strategies"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from .base_strategy import BaseStrategy, Signal


class RSIStrategy(BaseStrategy):
    """
    RSI Overbought/Oversold Strategy

    Buy when RSI crosses above oversold level
    Sell when RSI crosses below overbought level
    """

    name = "RSI超买超卖策略"
    description = "RSI超卖区域向上突破买入，超买区域向下突破卖出"

    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.period = self.get_param("period", 14)
        self.oversold = self.get_param("oversold", 30)
        self.overbought = self.get_param("overbought", 70)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()

        rs = avg_gain / avg_loss.replace(0, np.inf)
        df['rsi'] = 100 - (100 / (1 + rs))

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = self.calculate_indicators(df)
        signals = pd.Series(Signal.HOLD, index=df.index)

        # Cross above oversold
        buy_signal = (df['rsi'] > self.oversold) & (df['rsi'].shift(1) <= self.oversold)
        # Cross below overbought
        sell_signal = (df['rsi'] < self.overbought) & (df['rsi'].shift(1) >= self.overbought)

        signals[buy_signal] = Signal.BUY
        signals[sell_signal] = Signal.SELL

        return signals

    @classmethod
    def get_param_schema(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "period", "type": "int", "default": 14, "min": 5, "max": 50, "description": "RSI周期"},
            {"name": "oversold", "type": "int", "default": 30, "min": 10, "max": 40, "description": "超卖阈值"},
            {"name": "overbought", "type": "int", "default": 70, "min": 60, "max": 90, "description": "超买阈值"}
        ]


class KDJStrategy(BaseStrategy):
    """
    KDJ Strategy

    Buy when K crosses above D in oversold area
    Sell when K crosses below D in overbought area
    """

    name = "KDJ金叉死叉策略"
    description = "KDJ低位金叉买入，高位死叉卖出"

    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.n = self.get_param("n", 9)
        self.m1 = self.get_param("m1", 3)
        self.m2 = self.get_param("m2", 3)
        self.oversold = self.get_param("oversold", 20)
        self.overbought = self.get_param("overbought", 80)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        low_n = df['low'].rolling(window=self.n).min()
        high_n = df['high'].rolling(window=self.n).max()

        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        rsv = rsv.fillna(50)

        df['k'] = rsv.ewm(com=self.m1 - 1, adjust=False).mean()
        df['d'] = df['k'].ewm(com=self.m2 - 1, adjust=False).mean()
        df['j'] = 3 * df['k'] - 2 * df['d']

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = self.calculate_indicators(df)
        signals = pd.Series(Signal.HOLD, index=df.index)

        # K crosses above D
        k_cross_up = (df['k'] > df['d']) & (df['k'].shift(1) <= df['d'].shift(1))
        # K crosses below D
        k_cross_down = (df['k'] < df['d']) & (df['k'].shift(1) >= df['d'].shift(1))

        # In oversold area
        in_oversold = df['k'] < self.oversold
        # In overbought area
        in_overbought = df['k'] > self.overbought

        # Buy: golden cross in oversold or near oversold
        signals[k_cross_up & (df['k'].shift(1) < 50)] = Signal.BUY
        # Sell: death cross in overbought or near overbought
        signals[k_cross_down & (df['k'].shift(1) > 50)] = Signal.SELL

        return signals

    @classmethod
    def get_param_schema(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "n", "type": "int", "default": 9, "min": 5, "max": 30, "description": "RSV周期"},
            {"name": "m1", "type": "int", "default": 3, "min": 2, "max": 10, "description": "K平滑系数"},
            {"name": "m2", "type": "int", "default": 3, "min": 2, "max": 10, "description": "D平滑系数"},
            {"name": "oversold", "type": "int", "default": 20, "min": 10, "max": 30, "description": "超卖区域"},
            {"name": "overbought", "type": "int", "default": 80, "min": 70, "max": 90, "description": "超买区域"}
        ]


class BollingerStrategy(BaseStrategy):
    """
    Bollinger Bands Mean Reversion Strategy

    Buy when price touches lower band
    Sell when price touches upper band
    """

    name = "布林带均值回归策略"
    description = "价格触及下轨买入，触及上轨卖出"

    def __init__(self, params: Dict[str, Any] = None):
        super().__init__(params)
        self.period = self.get_param("period", 20)
        self.std_dev = self.get_param("std_dev", 2.0)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df['boll_mid'] = df['close'].rolling(window=self.period).mean()
        df['boll_std'] = df['close'].rolling(window=self.period).std()
        df['boll_upper'] = df['boll_mid'] + self.std_dev * df['boll_std']
        df['boll_lower'] = df['boll_mid'] - self.std_dev * df['boll_std']

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        df = self.calculate_indicators(df)
        signals = pd.Series(Signal.HOLD, index=df.index)

        # Price crosses below lower band then rebounds
        touch_lower = (df['low'] <= df['boll_lower']) & (df['close'] > df['boll_lower'])
        # Price crosses above upper band
        touch_upper = (df['high'] >= df['boll_upper']) & (df['close'] < df['boll_upper'])

        signals[touch_lower] = Signal.BUY
        signals[touch_upper] = Signal.SELL

        return signals

    @classmethod
    def get_param_schema(cls) -> List[Dict[str, Any]]:
        return [
            {"name": "period", "type": "int", "default": 20, "min": 10, "max": 50, "description": "布林带周期"},
            {"name": "std_dev", "type": "float", "default": 2.0, "min": 1.0, "max": 3.0, "description": "标准差倍数"}
        ]
