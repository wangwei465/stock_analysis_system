"""
价格区间预测模型
使用分位数回归预测价格区间
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False

from app.ml.features import FeatureEngineer


class PriceRangeModel:
    """价格区间预测模型"""

    def __init__(
        self,
        forward_days: int = 5,
        quantiles: List[float] = None
    ):
        """
        初始化模型

        Args:
            forward_days: 预测未来天数
            quantiles: 预测的分位数列表
        """
        self.forward_days = forward_days
        self.quantiles = quantiles or [0.1, 0.25, 0.5, 0.75, 0.9]
        self.models = {}
        self.feature_names = None

    def _create_target(self, df: pd.DataFrame) -> pd.Series:
        """创建目标变量 (未来收益率)"""
        return df['close'].shift(-self.forward_days) / df['close'] - 1

    def prepare_data(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.8
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """准备训练数据"""
        # 生成特征
        features = FeatureEngineer.generate_all_features(df)

        # 生成目标 (未来收益率)
        target = self._create_target(df)

        # 合并并删除缺失值
        data = pd.concat([features, target.rename('target')], axis=1)
        data = data.dropna()

        # 时序分割
        split_idx = int(len(data) * train_ratio)
        train_data = data.iloc[:split_idx]
        test_data = data.iloc[split_idx:]

        X_train = train_data.drop('target', axis=1)
        y_train = train_data['target']
        X_test = test_data.drop('target', axis=1)
        y_test = test_data['target']

        self.feature_names = X_train.columns.tolist()

        return X_train, y_train, X_test, y_test

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        num_boost_round: int = 300
    ) -> Dict:
        """
        训练多个分位数回归模型

        Args:
            X_train: 训练特征
            y_train: 训练目标 (收益率)
            num_boost_round: 迭代次数

        Returns:
            训练结果
        """
        if not HAS_LIGHTGBM:
            raise ImportError("LightGBM is not installed")

        train_data = lgb.Dataset(X_train, label=y_train)

        for q in self.quantiles:
            params = {
                'objective': 'quantile',
                'alpha': q,
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.8,
                'verbose': -1,
                'n_jobs': -1,
                'seed': 42
            }

            self.models[q] = lgb.train(
                params,
                train_data,
                num_boost_round=num_boost_round
            )

        return {
            'quantiles': self.quantiles,
            'models_trained': len(self.models)
        }

    def predict(self, X: pd.DataFrame) -> Dict[float, np.ndarray]:
        """
        预测各分位数的收益率

        Returns:
            各分位数的预测值
        """
        if not self.models:
            raise ValueError("Models not trained")

        X = X[self.feature_names]
        predictions = {}

        for q, model in self.models.items():
            predictions[q] = model.predict(X)

        return predictions

    def predict_single(self, df: pd.DataFrame, current_price: float = None) -> Dict:
        """
        预测单只股票的价格区间

        Args:
            df: 历史OHLCV数据
            current_price: 当前价格 (如不提供则使用最新收盘价)

        Returns:
            预测结果
        """
        if len(df) < 60:
            raise ValueError("Need at least 60 days of data")

        if current_price is None:
            current_price = df['close'].iloc[-1]

        # 生成特征
        features = FeatureEngineer.generate_all_features(df)
        latest_features = features.iloc[[-1]].dropna(axis=1)

        # 填充缺失特征
        for f in self.feature_names:
            if f not in latest_features.columns:
                latest_features[f] = 0

        latest_features = latest_features[self.feature_names]

        # 预测收益率
        return_predictions = {}
        for q, model in self.models.items():
            return_predictions[q] = float(model.predict(latest_features)[0])

        # 转换为价格区间
        price_predictions = {
            q: current_price * (1 + ret)
            for q, ret in return_predictions.items()
        }

        # 构建结果
        result = {
            'current_price': float(current_price),
            'forward_days': self.forward_days,
            'return_predictions': return_predictions,
            'price_predictions': price_predictions,
            'price_range': {
                'low': price_predictions.get(0.1, price_predictions.get(min(self.quantiles))),
                'mid': price_predictions.get(0.5, current_price),
                'high': price_predictions.get(0.9, price_predictions.get(max(self.quantiles)))
            },
            'expected_return': return_predictions.get(0.5, 0) * 100  # 百分比
        }

        return result


class QuickPriceRangePredictor:
    """
    快速价格区间预测器（无需训练）
    基于历史波动率估算
    """

    @staticmethod
    def predict(
        df: pd.DataFrame,
        forward_days: int = 5,
        confidence_levels: List[float] = None
    ) -> Dict:
        """
        基于历史波动率预测价格区间

        Args:
            df: OHLCV数据
            forward_days: 预测天数
            confidence_levels: 置信水平

        Returns:
            价格区间预测
        """
        confidence_levels = confidence_levels or [0.68, 0.95]

        if len(df) < 60:
            return {'error': '数据不足，需要至少60天数据'}

        current_price = df['close'].iloc[-1]

        # 计算历史日收益率
        returns = df['close'].pct_change().dropna()

        # 计算波动率指标
        daily_volatility = returns.std()
        annualized_volatility = daily_volatility * np.sqrt(252)

        # 计算不同周期的波动率
        vol_5d = returns.tail(5).std() * np.sqrt(5)
        vol_20d = returns.tail(20).std() * np.sqrt(20)
        vol_60d = returns.tail(60).std() * np.sqrt(60)

        # 预测期间波动率 (根号时间法则)
        forward_volatility = daily_volatility * np.sqrt(forward_days)

        # 计算各置信水平的价格区间
        # 假设收益率近似正态分布
        price_ranges = []
        for conf in confidence_levels:
            # z值对应的置信区间
            z = {0.68: 1, 0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(conf, 1.96)
            lower = current_price * (1 - z * forward_volatility)
            upper = current_price * (1 + z * forward_volatility)
            price_ranges.append({
                'confidence': conf,
                'lower': float(lower),
                'upper': float(upper),
                'range_pct': float(z * forward_volatility * 100 * 2)
            })

        # 基于趋势的预期价格
        # 使用近期收益率作为漂移项
        recent_return = returns.tail(20).mean()
        expected_return = recent_return * forward_days
        expected_price = current_price * (1 + expected_return)

        # 支撑位和阻力位 (近期高低点)
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()

        # ATR估算
        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        ], axis=1).max(axis=1)
        atr_14 = tr.tail(14).mean()

        return {
            'current_price': float(current_price),
            'forward_days': forward_days,
            'volatility': {
                'daily': float(daily_volatility * 100),
                'annualized': float(annualized_volatility * 100),
                'forward_period': float(forward_volatility * 100),
                'vol_5d': float(vol_5d * 100),
                'vol_20d': float(vol_20d * 100),
            },
            'price_ranges': price_ranges,
            'expected': {
                'price': float(expected_price),
                'return_pct': float(expected_return * 100)
            },
            'support_resistance': {
                'resistance': float(recent_high),
                'support': float(recent_low),
                'atr_14': float(atr_14)
            },
            'risk_assessment': {
                'atr_pct': float(atr_14 / current_price * 100),
                'volatility_level': (
                    '高' if annualized_volatility > 0.4 else
                    '中' if annualized_volatility > 0.2 else '低'
                )
            }
        }


class PriceTargetPredictor:
    """
    价格目标预测器
    结合技术分析和统计方法
    """

    @staticmethod
    def predict(df: pd.DataFrame, forward_days: int = 20) -> Dict:
        """
        预测价格目标

        Args:
            df: OHLCV数据
            forward_days: 预测天数

        Returns:
            价格目标预测
        """
        if len(df) < 120:
            return {'error': '数据不足'}

        current_price = df['close'].iloc[-1]

        # 1. 技术分析目标位
        # 布林带
        ma20 = df['close'].rolling(20).mean()
        std20 = df['close'].rolling(20).std()
        boll_upper = ma20 + 2 * std20
        boll_lower = ma20 - 2 * std20

        # 斐波那契回撤
        high_52w = df['high'].tail(252).max() if len(df) >= 252 else df['high'].max()
        low_52w = df['low'].tail(252).min() if len(df) >= 252 else df['low'].min()
        fib_range = high_52w - low_52w

        fib_levels = {
            0: low_52w,
            0.236: low_52w + fib_range * 0.236,
            0.382: low_52w + fib_range * 0.382,
            0.5: low_52w + fib_range * 0.5,
            0.618: low_52w + fib_range * 0.618,
            0.786: low_52w + fib_range * 0.786,
            1: high_52w
        }

        # 找到当前价格附近的斐波那契支撑/阻力
        fib_support = max([v for v in fib_levels.values() if v < current_price], default=low_52w)
        fib_resistance = min([v for v in fib_levels.values() if v > current_price], default=high_52w)

        # 2. 均线目标
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        ma10 = df['close'].rolling(10).mean().iloc[-1]
        ma20_val = ma20.iloc[-1]
        ma60 = df['close'].rolling(60).mean().iloc[-1]

        # 3. 趋势分析
        # 线性回归趋势
        recent = df.tail(60)
        x = np.arange(len(recent))
        slope, intercept = np.polyfit(x, recent['close'], 1)

        # 预测趋势目标
        trend_target = intercept + slope * (len(recent) + forward_days)

        # 4. 综合目标
        targets = {
            'bullish': {
                'conservative': float(min(boll_upper.iloc[-1], fib_resistance)),
                'moderate': float(fib_resistance),
                'aggressive': float(high_52w)
            },
            'bearish': {
                'conservative': float(max(boll_lower.iloc[-1], fib_support)),
                'moderate': float(fib_support),
                'aggressive': float(low_52w)
            },
            'trend_based': float(trend_target)
        }

        # 5. 概率评估
        # 基于历史数据估算达到目标的概率
        returns = df['close'].pct_change().dropna()
        vol = returns.std() * np.sqrt(forward_days)

        return {
            'current_price': float(current_price),
            'forward_days': forward_days,
            'targets': targets,
            'technical_levels': {
                'boll_upper': float(boll_upper.iloc[-1]),
                'boll_lower': float(boll_lower.iloc[-1]),
                'ma5': float(ma5),
                'ma10': float(ma10),
                'ma20': float(ma20_val),
                'ma60': float(ma60),
                'high_52w': float(high_52w),
                'low_52w': float(low_52w)
            },
            'fibonacci': fib_levels,
            'trend': {
                'slope': float(slope),
                'direction': '上升' if slope > 0 else '下降',
                'strength': abs(slope) / current_price * 100
            }
        }
