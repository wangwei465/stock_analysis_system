"""Technical indicator calculator"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional


class IndicatorCalculator:
    """Technical indicator calculator for stock data"""

    @staticmethod
    def calculate_ma(df: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
        """
        Calculate Moving Averages

        Args:
            df: DataFrame with 'close' column
            periods: List of MA periods

        Returns:
            DataFrame with MA columns
        """
        result = pd.DataFrame(index=df.index)
        for period in periods:
            result[f'ma{period}'] = df['close'].rolling(window=period).mean()
        return result

    @staticmethod
    def calculate_ema(df: pd.DataFrame, periods: List[int] = [12, 26]) -> pd.DataFrame:
        """Calculate Exponential Moving Averages"""
        result = pd.DataFrame(index=df.index)
        for period in periods:
            result[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        return result

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> pd.DataFrame:
        """
        Calculate MACD indicator

        Args:
            df: DataFrame with 'close' column
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)

        Returns:
            DataFrame with 'dif', 'dea', 'macd' columns
        """
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()

        dif = exp1 - exp2
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd = (dif - dea) * 2  # Multiply by 2 for visibility (histogram)

        return pd.DataFrame({
            'dif': dif,
            'dea': dea,
            'macd': macd
        }, index=df.index)

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate RSI (Relative Strength Index)

        Args:
            df: DataFrame with 'close' column
            period: RSI period (default 14)

        Returns:
            DataFrame with 'rsi' column (0-100)
        """
        delta = df['close'].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # Avoid division by zero
        rs = avg_gain / avg_loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))

        return pd.DataFrame({'rsi': rsi}, index=df.index)

    @staticmethod
    def calculate_kdj(
        df: pd.DataFrame,
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> pd.DataFrame:
        """
        Calculate KDJ indicator

        Args:
            df: DataFrame with 'high', 'low', 'close' columns
            n: Period for RSV calculation (default 9)
            m1: K smoothing factor (default 3)
            m2: D smoothing factor (default 3)

        Returns:
            DataFrame with 'k', 'd', 'j' columns
        """
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()

        # RSV calculation
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        rsv = rsv.fillna(50)  # Fill initial NaN with 50

        # K, D calculation using EMA-like smoothing
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d

        return pd.DataFrame({'k': k, 'd': d, 'j': j}, index=df.index)

    @staticmethod
    def calculate_boll(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> pd.DataFrame:
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with 'close' column
            period: Period for moving average (default 20)
            std_dev: Standard deviation multiplier (default 2)

        Returns:
            DataFrame with 'upper', 'mid', 'lower' columns
        """
        mid = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        upper = mid + std_dev * std
        lower = mid - std_dev * std

        return pd.DataFrame({
            'upper': upper,
            'mid': mid,
            'lower': lower
        }, index=df.index)

    @staticmethod
    def calculate_volume_ma(df: pd.DataFrame, periods: List[int] = [5, 10]) -> pd.DataFrame:
        """Calculate Volume Moving Averages"""
        result = pd.DataFrame(index=df.index)
        for period in periods:
            result[f'vol_ma{period}'] = df['volume'].rolling(window=period).mean()
        return result

    @staticmethod
    def calculate_all(
        df: pd.DataFrame,
        ma_periods: List[int] = [5, 10, 20, 60]
    ) -> Dict[str, any]:
        """
        Calculate all indicators at once

        Args:
            df: DataFrame with OHLCV data
            ma_periods: Periods for MA calculation

        Returns:
            Dict with all indicator results
        """
        return {
            'ma': IndicatorCalculator.calculate_ma(df, ma_periods),
            'macd': IndicatorCalculator.calculate_macd(df),
            'rsi': IndicatorCalculator.calculate_rsi(df),
            'kdj': IndicatorCalculator.calculate_kdj(df),
            'boll': IndicatorCalculator.calculate_boll(df),
            'volume_ma': IndicatorCalculator.calculate_volume_ma(df)
        }


def format_indicator_for_chart(
    df: pd.DataFrame,
    indicator_series: pd.Series,
    date_column: str = 'date'
) -> List[Dict]:
    """
    Format indicator data for frontend chart

    Args:
        df: Original DataFrame with date column
        indicator_series: Indicator values series
        date_column: Name of date column

    Returns:
        List of {time, value} dicts
    """
    result = []
    for i, (idx, value) in enumerate(indicator_series.items()):
        if pd.notna(value):
            date_val = df.iloc[i][date_column]
            if isinstance(date_val, pd.Timestamp):
                date_str = date_val.strftime('%Y-%m-%d')
            else:
                date_str = str(date_val)

            result.append({
                'time': date_str,
                'value': round(float(value), 4)
            })

    return result
