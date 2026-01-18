"""
ML特征工程模块
用于生成价格预测所需的特征
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Tuple
from app.core.indicator_calculator import IndicatorCalculator


class FeatureEngineer:
    """特征工程类"""

    # 默认特征窗口
    DEFAULT_WINDOWS = [5, 10, 20, 60]

    @staticmethod
    def calculate_returns(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
        """
        计算收益率特征

        Args:
            df: 包含close列的DataFrame
            windows: 回看窗口列表

        Returns:
            包含收益率特征的DataFrame
        """
        windows = windows or FeatureEngineer.DEFAULT_WINDOWS
        features = pd.DataFrame(index=df.index)

        # 日收益率
        features['return_1d'] = df['close'].pct_change()

        # 多周期收益率
        for w in windows:
            features[f'return_{w}d'] = df['close'].pct_change(w)

        # 对数收益率
        features['log_return_1d'] = np.log(df['close'] / df['close'].shift(1))

        return features

    @staticmethod
    def calculate_momentum(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
        """
        计算动量特征

        Args:
            df: 包含OHLCV的DataFrame
            windows: 回看窗口列表

        Returns:
            包含动量特征的DataFrame
        """
        windows = windows or FeatureEngineer.DEFAULT_WINDOWS
        features = pd.DataFrame(index=df.index)

        # 价格动量 (Price - Price_n) / Price_n
        for w in windows:
            features[f'momentum_{w}d'] = (df['close'] - df['close'].shift(w)) / df['close'].shift(w)

        # ROC (Rate of Change)
        for w in windows:
            features[f'roc_{w}d'] = df['close'].pct_change(w) * 100

        # 相对位置 (当前价格在N日高低点中的位置)
        for w in windows:
            high_n = df['high'].rolling(w).max()
            low_n = df['low'].rolling(w).min()
            features[f'price_position_{w}d'] = (df['close'] - low_n) / (high_n - low_n + 1e-8)

        return features

    @staticmethod
    def calculate_volatility(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
        """
        计算波动率特征

        Args:
            df: 包含OHLCV的DataFrame
            windows: 回看窗口列表

        Returns:
            包含波动率特征的DataFrame
        """
        windows = windows or FeatureEngineer.DEFAULT_WINDOWS
        features = pd.DataFrame(index=df.index)

        # 日内波动率
        features['intraday_range'] = (df['high'] - df['low']) / df['close']

        # 收益率标准差
        returns = df['close'].pct_change()
        for w in windows:
            features[f'volatility_{w}d'] = returns.rolling(w).std()

        # 真实波动幅度 (ATR normalized)
        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        ], axis=1).max(axis=1)

        for w in windows:
            features[f'atr_{w}d'] = tr.rolling(w).mean() / df['close']

        # 价格振幅
        for w in windows:
            features[f'amplitude_{w}d'] = (
                df['high'].rolling(w).max() - df['low'].rolling(w).min()
            ) / df['close']

        return features

    @staticmethod
    def calculate_volume_features(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
        """
        计算成交量特征

        Args:
            df: 包含volume列的DataFrame
            windows: 回看窗口列表

        Returns:
            包含成交量特征的DataFrame
        """
        windows = windows or FeatureEngineer.DEFAULT_WINDOWS
        features = pd.DataFrame(index=df.index)

        # 成交量变化率
        features['volume_change'] = df['volume'].pct_change()

        # 成交量移动平均比率
        for w in windows:
            vol_ma = df['volume'].rolling(w).mean()
            features[f'volume_ratio_{w}d'] = df['volume'] / (vol_ma + 1e-8)

        # 成交量标准差
        for w in windows:
            features[f'volume_std_{w}d'] = df['volume'].rolling(w).std() / (df['volume'].rolling(w).mean() + 1e-8)

        # OBV特征 (On-Balance Volume)
        obv = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        features['obv_change'] = obv.pct_change()

        # 量价相关性
        for w in windows:
            features[f'price_volume_corr_{w}d'] = (
                df['close'].rolling(w).corr(df['volume'])
            )

        return features

    @staticmethod
    def calculate_technical_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标特征

        Args:
            df: 包含OHLCV的DataFrame

        Returns:
            包含技术指标特征的DataFrame
        """
        features = pd.DataFrame(index=df.index)

        # MA特征
        ma_periods = [5, 10, 20, 60]
        ma_df = IndicatorCalculator.calculate_ma(df, ma_periods)

        for period in ma_periods:
            col = f'ma{period}'
            if col in ma_df.columns:
                # 价格与MA的偏离度
                features[f'ma{period}_deviation'] = (df['close'] - ma_df[col]) / ma_df[col]

        # MA交叉信号
        if 'ma5' in ma_df.columns and 'ma20' in ma_df.columns:
            features['ma5_ma20_cross'] = (ma_df['ma5'] > ma_df['ma20']).astype(int)
            features['ma5_ma20_diff'] = (ma_df['ma5'] - ma_df['ma20']) / ma_df['ma20']

        # MACD特征
        macd_df = IndicatorCalculator.calculate_macd(df)
        if 'dif' in macd_df.columns:
            features['macd_dif'] = macd_df['dif']
            features['macd_dea'] = macd_df['dea']
            features['macd_hist'] = macd_df['macd']
            features['macd_hist_change'] = macd_df['macd'].diff()

        # RSI特征
        rsi_df = IndicatorCalculator.calculate_rsi(df, 14)
        if 'rsi' in rsi_df.columns:
            features['rsi_14'] = rsi_df['rsi']
            features['rsi_overbought'] = (rsi_df['rsi'] > 70).astype(int)
            features['rsi_oversold'] = (rsi_df['rsi'] < 30).astype(int)

        # KDJ特征
        kdj_df = IndicatorCalculator.calculate_kdj(df)
        if 'k' in kdj_df.columns:
            features['kdj_k'] = kdj_df['k']
            features['kdj_d'] = kdj_df['d']
            features['kdj_j'] = kdj_df['j']
            features['kdj_cross'] = (kdj_df['k'] > kdj_df['d']).astype(int)

        # BOLL特征
        boll_df = IndicatorCalculator.calculate_boll(df)
        if 'upper' in boll_df.columns:
            features['boll_width'] = (boll_df['upper'] - boll_df['lower']) / boll_df['mid']
            features['boll_position'] = (df['close'] - boll_df['lower']) / (boll_df['upper'] - boll_df['lower'] + 1e-8)

        return features

    @staticmethod
    def calculate_trend_features(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
        """
        计算趋势特征

        Args:
            df: 包含OHLCV的DataFrame
            windows: 回看窗口列表

        Returns:
            包含趋势特征的DataFrame
        """
        windows = windows or FeatureEngineer.DEFAULT_WINDOWS
        features = pd.DataFrame(index=df.index)

        # 线性回归斜率
        for w in windows:
            def calc_slope(series):
                if len(series) < w:
                    return np.nan
                x = np.arange(len(series))
                slope = np.polyfit(x, series, 1)[0]
                return slope / (series.mean() + 1e-8)  # 归一化

            features[f'trend_slope_{w}d'] = df['close'].rolling(w).apply(calc_slope, raw=True)

        # 上涨天数占比
        price_up = (df['close'] > df['close'].shift(1)).astype(int)
        for w in windows:
            features[f'up_days_ratio_{w}d'] = price_up.rolling(w).mean()

        # 连续涨跌天数
        def count_consecutive(series):
            if series.iloc[-1] == 1:
                # 连续上涨
                count = 0
                for v in series.iloc[::-1]:
                    if v == 1:
                        count += 1
                    else:
                        break
                return count
            else:
                # 连续下跌
                count = 0
                for v in series.iloc[::-1]:
                    if v == 0:
                        count -= 1
                    else:
                        break
                return count

        features['consecutive_trend'] = price_up.rolling(20).apply(count_consecutive, raw=False)

        return features

    @staticmethod
    def calculate_pattern_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算K线形态特征

        Args:
            df: 包含OHLCV的DataFrame

        Returns:
            包含形态特征的DataFrame
        """
        features = pd.DataFrame(index=df.index)

        # 实体比例
        body = abs(df['close'] - df['open'])
        shadow = df['high'] - df['low']
        features['body_ratio'] = body / (shadow + 1e-8)

        # 上影线比例
        upper_shadow = df['high'] - df[['close', 'open']].max(axis=1)
        features['upper_shadow_ratio'] = upper_shadow / (shadow + 1e-8)

        # 下影线比例
        lower_shadow = df[['close', 'open']].min(axis=1) - df['low']
        features['lower_shadow_ratio'] = lower_shadow / (shadow + 1e-8)

        # 阳线/阴线
        features['is_bullish'] = (df['close'] > df['open']).astype(int)

        # 跳空缺口
        features['gap_up'] = ((df['low'] > df['high'].shift(1))).astype(int)
        features['gap_down'] = ((df['high'] < df['low'].shift(1))).astype(int)

        return features

    @classmethod
    def generate_all_features(
        cls,
        df: pd.DataFrame,
        windows: List[int] = None,
        include_technical: bool = True
    ) -> pd.DataFrame:
        """
        生成所有特征

        Args:
            df: 包含OHLCV的DataFrame
            windows: 回看窗口列表
            include_technical: 是否包含技术指标特征

        Returns:
            包含所有特征的DataFrame
        """
        all_features = pd.DataFrame(index=df.index)

        # 基础价格特征
        all_features = pd.concat([
            all_features,
            cls.calculate_returns(df, windows),
            cls.calculate_momentum(df, windows),
            cls.calculate_volatility(df, windows),
            cls.calculate_volume_features(df, windows),
            cls.calculate_trend_features(df, windows),
            cls.calculate_pattern_features(df),
        ], axis=1)

        # 技术指标特征
        if include_technical:
            all_features = pd.concat([
                all_features,
                cls.calculate_technical_features(df)
            ], axis=1)

        # 移除无穷大和NaN
        all_features = all_features.replace([np.inf, -np.inf], np.nan)

        return all_features

    @staticmethod
    def create_labels(
        df: pd.DataFrame,
        forward_days: int = 5,
        threshold: float = 0.02
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        创建预测标签

        Args:
            df: 包含close列的DataFrame
            forward_days: 向前预测天数
            threshold: 涨跌阈值

        Returns:
            direction: 方向标签 (1=上涨, 0=下跌)
            return_pct: 收益率标签
            signal: 信号标签 (2=强买, 1=买, 0=持有, -1=卖, -2=强卖)
        """
        # 未来收益率
        future_return = df['close'].shift(-forward_days) / df['close'] - 1

        # 方向标签
        direction = (future_return > 0).astype(int)

        # 信号标签
        signal = pd.Series(0, index=df.index)
        signal[future_return > threshold * 2] = 2  # 强买
        signal[(future_return > threshold) & (future_return <= threshold * 2)] = 1  # 买
        signal[(future_return < -threshold) & (future_return >= -threshold * 2)] = -1  # 卖
        signal[future_return < -threshold * 2] = -2  # 强卖

        return direction, future_return, signal
