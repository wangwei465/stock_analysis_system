"""
买卖信号生成器
综合多种预测模型生成交易信号
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.ml.features import FeatureEngineer
from app.ml.models.price_direction import QuickPredictionModel
from app.ml.models.price_range import QuickPriceRangePredictor
from app.core.indicator_calculator import IndicatorCalculator


class SignalType(Enum):
    """信号类型"""
    STRONG_BUY = 2
    BUY = 1
    HOLD = 0
    SELL = -1
    STRONG_SELL = -2


@dataclass
class TradingSignal:
    """交易信号"""
    signal: SignalType
    signal_label: str
    confidence: float
    reasons: List[str]
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None


class SignalGenerator:
    """
    综合信号生成器
    结合技术指标、价格预测、波动率分析生成交易信号
    """

    def __init__(
        self,
        risk_tolerance: str = 'moderate',  # conservative, moderate, aggressive
        holding_period: int = 5
    ):
        """
        初始化信号生成器

        Args:
            risk_tolerance: 风险偏好
            holding_period: 预期持仓周期(天)
        """
        self.risk_tolerance = risk_tolerance
        self.holding_period = holding_period

        # 风险偏好对应的参数
        self.risk_params = {
            'conservative': {
                'signal_threshold': 0.6,
                'stop_loss_atr_mult': 1.5,
                'take_profit_atr_mult': 2.0,
                'min_confidence': 0.6
            },
            'moderate': {
                'signal_threshold': 0.4,
                'stop_loss_atr_mult': 2.0,
                'take_profit_atr_mult': 3.0,
                'min_confidence': 0.4
            },
            'aggressive': {
                'signal_threshold': 0.2,
                'stop_loss_atr_mult': 2.5,
                'take_profit_atr_mult': 4.0,
                'min_confidence': 0.2
            }
        }

    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        生成综合交易信号

        Args:
            df: OHLCV数据

        Returns:
            交易信号详情
        """
        if len(df) < 60:
            return {
                'signal': 0,
                'signal_label': '数据不足',
                'confidence': 0,
                'reasons': ['需要至少60天历史数据'],
                'components': {}
            }

        current_price = df['close'].iloc[-1]
        params = self.risk_params[self.risk_tolerance]

        # 收集各维度的信号
        components = {}
        scores = []
        reasons = []

        # 1. 技术指标信号
        tech_signal = self._analyze_technical_indicators(df)
        components['technical'] = tech_signal
        scores.append(tech_signal['score'] * 0.3)  # 30%权重
        reasons.extend(tech_signal['reasons'])

        # 2. 趋势信号
        trend_signal = self._analyze_trend(df)
        components['trend'] = trend_signal
        scores.append(trend_signal['score'] * 0.25)  # 25%权重
        reasons.extend(trend_signal['reasons'])

        # 3. 动量信号
        momentum_signal = self._analyze_momentum(df)
        components['momentum'] = momentum_signal
        scores.append(momentum_signal['score'] * 0.2)  # 20%权重
        reasons.extend(momentum_signal['reasons'])

        # 4. 波动率和风险信号
        volatility_signal = self._analyze_volatility(df)
        components['volatility'] = volatility_signal
        scores.append(volatility_signal['score'] * 0.15)  # 15%权重
        reasons.extend(volatility_signal['reasons'])

        # 5. 成交量信号
        volume_signal = self._analyze_volume(df)
        components['volume'] = volume_signal
        scores.append(volume_signal['score'] * 0.1)  # 10%权重
        reasons.extend(volume_signal['reasons'])

        # 计算综合得分
        total_score = sum(scores)
        confidence = min(abs(total_score) / params['signal_threshold'], 1)

        # 确定信号类型
        if total_score >= params['signal_threshold'] * 2:
            signal = SignalType.STRONG_BUY
            signal_label = '强烈买入'
        elif total_score >= params['signal_threshold']:
            signal = SignalType.BUY
            signal_label = '买入'
        elif total_score <= -params['signal_threshold'] * 2:
            signal = SignalType.STRONG_SELL
            signal_label = '强烈卖出'
        elif total_score <= -params['signal_threshold']:
            signal = SignalType.SELL
            signal_label = '卖出'
        else:
            signal = SignalType.HOLD
            signal_label = '持有/观望'

        # 计算止损止盈位
        atr = self._calculate_atr(df)
        stop_loss = None
        take_profit = None
        risk_reward = None

        if signal.value > 0:  # 买入信号
            stop_loss = current_price - atr * params['stop_loss_atr_mult']
            take_profit = current_price + atr * params['take_profit_atr_mult']
            risk_reward = params['take_profit_atr_mult'] / params['stop_loss_atr_mult']
        elif signal.value < 0:  # 卖出信号
            stop_loss = current_price + atr * params['stop_loss_atr_mult']
            take_profit = current_price - atr * params['take_profit_atr_mult']
            risk_reward = params['take_profit_atr_mult'] / params['stop_loss_atr_mult']

        # 过滤原因,只保留主要的
        main_reasons = [r for r in reasons if r][:5]

        return {
            'signal': signal.value,
            'signal_label': signal_label,
            'confidence': float(confidence),
            'score': float(total_score),
            'reasons': main_reasons,
            'entry_price': float(current_price),
            'stop_loss': float(stop_loss) if stop_loss else None,
            'take_profit': float(take_profit) if take_profit else None,
            'risk_reward_ratio': float(risk_reward) if risk_reward else None,
            'atr': float(atr),
            'components': components,
            'risk_tolerance': self.risk_tolerance,
            'holding_period': self.holding_period
        }

    def _analyze_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """分析技术指标"""
        score = 0
        reasons = []

        # RSI
        rsi_df = IndicatorCalculator.calculate_rsi(df, 14)
        if 'rsi' in rsi_df.columns:
            rsi = rsi_df['rsi'].iloc[-1]
            rsi_prev = rsi_df['rsi'].iloc[-2] if len(rsi_df) > 1 else rsi

            if rsi < 30:
                score += 0.4
                reasons.append(f'RSI超卖({rsi:.1f})')
            elif rsi > 70:
                score -= 0.4
                reasons.append(f'RSI超买({rsi:.1f})')
            elif rsi < 45 and rsi > rsi_prev:
                score += 0.2
                reasons.append('RSI低位回升')
            elif rsi > 55 and rsi < rsi_prev:
                score -= 0.2
                reasons.append('RSI高位回落')

        # MACD
        macd_df = IndicatorCalculator.calculate_macd(df)
        if 'macd' in macd_df.columns:
            macd_hist = macd_df['macd'].iloc[-1]
            macd_hist_prev = macd_df['macd'].iloc[-2] if len(macd_df) > 1 else 0
            dif = macd_df['dif'].iloc[-1]
            dea = macd_df['dea'].iloc[-1]

            # 金叉/死叉
            if dif > dea and macd_df['dif'].iloc[-2] <= macd_df['dea'].iloc[-2]:
                score += 0.5
                reasons.append('MACD金叉')
            elif dif < dea and macd_df['dif'].iloc[-2] >= macd_df['dea'].iloc[-2]:
                score -= 0.5
                reasons.append('MACD死叉')

            # 柱状图
            if macd_hist > 0 and macd_hist > macd_hist_prev:
                score += 0.2
            elif macd_hist < 0 and macd_hist < macd_hist_prev:
                score -= 0.2

        # KDJ
        kdj_df = IndicatorCalculator.calculate_kdj(df)
        if 'k' in kdj_df.columns:
            k = kdj_df['k'].iloc[-1]
            d = kdj_df['d'].iloc[-1]
            j = kdj_df['j'].iloc[-1]

            if j < 0:
                score += 0.3
                reasons.append('KDJ超卖')
            elif j > 100:
                score -= 0.3
                reasons.append('KDJ超买')

            # 金叉
            if k > d and kdj_df['k'].iloc[-2] <= kdj_df['d'].iloc[-2]:
                if k < 50:
                    score += 0.3
                    reasons.append('KDJ低位金叉')
            elif k < d and kdj_df['k'].iloc[-2] >= kdj_df['d'].iloc[-2]:
                if k > 50:
                    score -= 0.3
                    reasons.append('KDJ高位死叉')

        # 布林带
        boll_df = IndicatorCalculator.calculate_boll(df)
        if 'upper' in boll_df.columns:
            close = df['close'].iloc[-1]
            upper = boll_df['upper'].iloc[-1]
            lower = boll_df['lower'].iloc[-1]
            mid = boll_df['mid'].iloc[-1]

            if close <= lower:
                score += 0.3
                reasons.append('价格触及布林下轨')
            elif close >= upper:
                score -= 0.3
                reasons.append('价格触及布林上轨')

        return {
            'score': float(np.clip(score, -1, 1)),
            'reasons': reasons
        }

    def _analyze_trend(self, df: pd.DataFrame) -> Dict:
        """分析趋势"""
        score = 0
        reasons = []

        # 均线系统
        ma_df = IndicatorCalculator.calculate_ma(df, [5, 10, 20, 60])
        close = df['close'].iloc[-1]

        if all(col in ma_df.columns for col in ['ma5', 'ma10', 'ma20', 'ma60']):
            ma5 = ma_df['ma5'].iloc[-1]
            ma10 = ma_df['ma10'].iloc[-1]
            ma20 = ma_df['ma20'].iloc[-1]
            ma60 = ma_df['ma60'].iloc[-1]

            # 多头排列
            if ma5 > ma10 > ma20 > ma60:
                score += 0.5
                reasons.append('均线多头排列')
            elif ma5 < ma10 < ma20 < ma60:
                score -= 0.5
                reasons.append('均线空头排列')
            else:
                # 均线交织，趋势不明朗
                reasons.append('均线交织震荡')

            # 价格与均线关系
            if close > ma20:
                score += 0.2
                if not any('价格' in r for r in reasons):
                    reasons.append(f'价格位于MA20上方')
            else:
                score -= 0.2
                if not any('价格' in r for r in reasons):
                    reasons.append(f'价格位于MA20下方')

            # 均线斜率
            if len(ma_df) > 5:
                ma20_slope = (ma_df['ma20'].iloc[-1] - ma_df['ma20'].iloc[-5]) / ma_df['ma20'].iloc[-5]
                if ma20_slope > 0.02:
                    score += 0.2
                    reasons.append('MA20向上')
                elif ma20_slope < -0.02:
                    score -= 0.2
                    reasons.append('MA20向下')
                else:
                    reasons.append('MA20走平')

        # 线性回归趋势
        if len(df) >= 20:
            recent = df.tail(20)
            x = np.arange(len(recent))
            slope, _ = np.polyfit(x, recent['close'], 1)
            slope_pct = slope / df['close'].iloc[-1] * 100

            if slope_pct > 0.5:
                score += 0.3
                reasons.append(f'短期上升趋势')
            elif slope_pct < -0.5:
                score -= 0.3
                reasons.append(f'短期下降趋势')
            else:
                if not any('趋势' in r for r in reasons):
                    reasons.append('短期横盘整理')

        # 确保至少有一个理由
        if not reasons:
            reasons.append('趋势特征不明显')

        return {
            'score': float(np.clip(score, -1, 1)),
            'reasons': reasons
        }

    def _analyze_momentum(self, df: pd.DataFrame) -> Dict:
        """分析动量"""
        score = 0
        reasons = []

        # 收益率动量
        returns_5d = (df['close'].iloc[-1] / df['close'].iloc[-5] - 1) * 100 if len(df) > 5 else 0
        returns_20d = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100 if len(df) > 20 else 0

        # 动量方向
        if returns_5d > 5:
            score += 0.3
            reasons.append(f'5日涨幅{returns_5d:.1f}%')
        elif returns_5d < -5:
            score -= 0.3
            reasons.append(f'5日跌幅{returns_5d:.1f}%')

        # 动量加速
        if len(df) > 10:
            returns_prev_5d = (df['close'].iloc[-5] / df['close'].iloc[-10] - 1) * 100
            if returns_5d > 0 and returns_5d > returns_prev_5d:
                score += 0.2
                reasons.append('上涨动能增强')
            elif returns_5d < 0 and returns_5d < returns_prev_5d:
                score -= 0.2
                reasons.append('下跌动能增强')

        # ROC
        if len(df) > 10:
            roc = (df['close'].iloc[-1] / df['close'].iloc[-10] - 1) * 100
            if roc > 10:
                score += 0.2
            elif roc < -10:
                score -= 0.2

        return {
            'score': float(np.clip(score, -1, 1)),
            'reasons': reasons
        }

    def _analyze_volatility(self, df: pd.DataFrame) -> Dict:
        """分析波动率"""
        score = 0
        reasons = []

        returns = df['close'].pct_change().dropna()
        vol_20d = returns.tail(20).std() * np.sqrt(252) * 100

        # 波动率水平
        if vol_20d > 50:
            score -= 0.2
            reasons.append(f'高波动率({vol_20d:.0f}%年化)')
        elif vol_20d < 20:
            score += 0.1
            reasons.append(f'低波动率({vol_20d:.0f}%年化)')

        # 波动率变化
        if len(returns) > 40:
            vol_prev = returns.iloc[-40:-20].std() * np.sqrt(252) * 100
            if vol_20d < vol_prev * 0.7:
                score += 0.1
                reasons.append('波动率收敛')
            elif vol_20d > vol_prev * 1.5:
                reasons.append('波动率扩大')

        return {
            'score': float(np.clip(score, -1, 1)),
            'reasons': reasons
        }

    def _analyze_volume(self, df: pd.DataFrame) -> Dict:
        """分析成交量"""
        score = 0
        reasons = []

        if 'volume' not in df.columns:
            return {'score': 0, 'reasons': ['无成交量数据']}

        vol = df['volume'].iloc[-1]
        vol_ma20 = df['volume'].tail(20).mean()
        price_change = df['close'].iloc[-1] / df['close'].iloc[-2] - 1

        vol_ratio = vol / vol_ma20 if vol_ma20 > 0 else 1

        # 放量上涨
        if vol_ratio > 2 and price_change > 0.02:
            score += 0.4
            reasons.append(f'放量上涨(量比{vol_ratio:.1f})')
        # 放量下跌
        elif vol_ratio > 2 and price_change < -0.02:
            score -= 0.4
            reasons.append(f'放量下跌(量比{vol_ratio:.1f})')
        # 缩量上涨
        elif vol_ratio < 0.5 and price_change > 0.02:
            score += 0.1
            reasons.append('缩量上涨')
        # 缩量下跌
        elif vol_ratio < 0.5 and price_change < -0.02:
            score -= 0.1
            reasons.append('缩量下跌')
        # 量价配合一般
        else:
            if vol_ratio > 1.5:
                reasons.append(f'成交量放大(量比{vol_ratio:.1f})')
            elif vol_ratio < 0.7:
                reasons.append(f'成交量萎缩(量比{vol_ratio:.1f})')
            else:
                reasons.append(f'成交量正常(量比{vol_ratio:.1f})')

        return {
            'score': float(np.clip(score, -1, 1)),
            'reasons': reasons
        }

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算ATR"""
        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        ], axis=1).max(axis=1)

        return tr.tail(period).mean()


class ComprehensivePredictor:
    """
    综合预测器
    整合所有预测模型
    """

    @staticmethod
    def predict(df: pd.DataFrame, forward_days: int = 5) -> Dict:
        """
        生成综合预测报告

        Args:
            df: OHLCV数据
            forward_days: 预测天数

        Returns:
            综合预测结果
        """
        result = {
            'stock_info': {
                'current_price': float(df['close'].iloc[-1]),
                'date': str(df.index[-1]) if hasattr(df.index[-1], 'strftime') else str(df.index[-1])
            }
        }

        # 1. 方向预测
        direction = QuickPredictionModel.predict(df)
        result['direction'] = direction

        # 2. 价格区间预测
        price_range = QuickPriceRangePredictor.predict(df, forward_days)
        result['price_range'] = price_range

        # 3. 交易信号
        signal_gen = SignalGenerator(risk_tolerance='moderate', holding_period=forward_days)
        signal = signal_gen.generate_signal(df)
        result['signal'] = signal

        # 4. 风险评估
        returns = df['close'].pct_change().dropna()
        result['risk'] = {
            'daily_volatility': float(returns.std() * 100),
            'annualized_volatility': float(returns.std() * np.sqrt(252) * 100),
            'max_drawdown_20d': float(
                (df['close'].tail(20) / df['close'].tail(20).cummax() - 1).min() * 100
            ),
            'var_95': float(returns.quantile(0.05) * 100),  # 95% VaR
            'cvar_95': float(returns[returns <= returns.quantile(0.05)].mean() * 100)  # CVaR
        }

        # 5. 综合建议
        result['recommendation'] = ComprehensivePredictor._generate_recommendation(
            direction, signal, price_range
        )

        return result

    @staticmethod
    def _generate_recommendation(direction: Dict, signal: Dict, price_range: Dict) -> Dict:
        """生成综合建议"""
        # 综合评分
        direction_score = direction.get('score', 0)
        signal_score = signal.get('score', 0)

        avg_score = (direction_score + signal_score) / 2

        if avg_score > 0.5:
            action = '积极买入'
            risk_level = '中等'
        elif avg_score > 0.2:
            action = '适度买入'
            risk_level = '较低'
        elif avg_score < -0.5:
            action = '建议卖出'
            risk_level = '较高'
        elif avg_score < -0.2:
            action = '减仓'
            risk_level = '中等'
        else:
            action = '观望'
            risk_level = '低'

        return {
            'action': action,
            'risk_level': risk_level,
            'score': float(avg_score),
            'summary': f"{signal.get('signal_label', '观望')} - {direction.get('direction_label', '震荡')}"
        }
