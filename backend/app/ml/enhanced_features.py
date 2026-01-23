"""
增强特征工程模块
====================================
提供资金流向、市场情绪等高级特征计算功能。

本模块包含：
- 资金流向特征（主力资金、散户资金、北向资金等）
- 市场情绪特征（涨跌停统计、市场宽度等）
- 行业轮动特征

依赖：
- AKShare：用于获取实时资金流向数据
- 若 AKShare 不可用，将返回默认值
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

# =============================================================================
# AKShare 延迟导入（可选依赖）
# =============================================================================
_ak = None
HAS_AKSHARE = True


def get_akshare():
    """
    延迟加载 AKShare 模块

    Returns:
        akshare 模块对象，若导入失败则返回 None
    """
    global _ak, HAS_AKSHARE
    if _ak is None:
        try:
            import akshare as ak
            _ak = ak
        except ImportError:
            HAS_AKSHARE = False
            _ak = None
    return _ak


# =============================================================================
# 数据类定义
# =============================================================================
@dataclass
class CapitalFlowData:
    """
    资金流向数据结构

    Attributes:
        main_net_inflow: 主力净流入（万元）
        retail_net_inflow: 散户净流入（万元）
        super_large_inflow: 超大单净流入（万元）
        large_inflow: 大单净流入（万元）
        medium_inflow: 中单净流入（万元）
        small_inflow: 小单净流入（万元）
        north_net_inflow: 北向资金净流入（万元）
    """
    main_net_inflow: float = 0.0
    retail_net_inflow: float = 0.0
    super_large_inflow: float = 0.0
    large_inflow: float = 0.0
    medium_inflow: float = 0.0
    small_inflow: float = 0.0
    north_net_inflow: float = 0.0


@dataclass
class MarketSentimentData:
    """
    市场情绪数据结构

    Attributes:
        up_count: 上涨家数
        down_count: 下跌家数
        flat_count: 平盘家数
        limit_up_count: 涨停家数
        limit_down_count: 跌停家数
        advance_decline_ratio: 涨跌比
        market_strength: 市场强度指数 (0-100)
    """
    up_count: int = 0
    down_count: int = 0
    flat_count: int = 0
    limit_up_count: int = 0
    limit_down_count: int = 0
    advance_decline_ratio: float = 1.0
    market_strength: float = 50.0


# =============================================================================
# 资金流向特征计算器
# =============================================================================
class CapitalFlowAnalyzer:
    """
    资金流向分析器
    ====================================
    通过 AKShare 获取个股资金流向数据，计算相关特征。

    使用示例：
    >>> analyzer = CapitalFlowAnalyzer()
    >>> flow_data = analyzer.get_stock_capital_flow("000001")
    >>> signal = analyzer.generate_capital_flow_signal(flow_data)
    """

    def __init__(self):
        """初始化资金流向分析器"""
        self.cache = {}  # 简单缓存，避免频繁请求
        self.cache_time = {}

    def get_stock_capital_flow(self, stock_code: str) -> CapitalFlowData:
        """
        获取个股资金流向数据

        通过 AKShare 的 stock_individual_fund_flow 接口获取数据。

        Args:
            stock_code: 股票代码（如 "000001" 或 "sh600000"）

        Returns:
            CapitalFlowData: 资金流向数据对象
        """
        # 检查缓存（5分钟有效期）
        cache_key = f"flow_{stock_code}"
        if cache_key in self.cache:
            if datetime.now() - self.cache_time.get(cache_key, datetime.min) < timedelta(minutes=5):
                return self.cache[cache_key]

        ak = get_akshare()
        if ak is None:
            return CapitalFlowData()

        try:
            # 清理股票代码格式
            code = stock_code.replace('sh', '').replace('sz', '').replace('.', '')

            # 获取个股资金流向数据
            # AKShare 接口: stock_individual_fund_flow
            df = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith('6') else "sz")

            if df is not None and not df.empty:
                # 取最近一条数据
                latest = df.iloc[-1]

                flow_data = CapitalFlowData(
                    main_net_inflow=float(latest.get('主力净流入-净额', 0) or 0),
                    retail_net_inflow=float(latest.get('小单净流入-净额', 0) or 0) + float(latest.get('中单净流入-净额', 0) or 0),
                    super_large_inflow=float(latest.get('超大单净流入-净额', 0) or 0),
                    large_inflow=float(latest.get('大单净流入-净额', 0) or 0),
                    medium_inflow=float(latest.get('中单净流入-净额', 0) or 0),
                    small_inflow=float(latest.get('小单净流入-净额', 0) or 0),
                )

                # 更新缓存
                self.cache[cache_key] = flow_data
                self.cache_time[cache_key] = datetime.now()

                return flow_data

        except Exception as e:
            print(f"获取资金流向数据失败: {e}")

        return CapitalFlowData()

    def get_north_capital_flow(self) -> float:
        """
        获取北向资金净流入

        Returns:
            float: 北向资金净流入（亿元）
        """
        ak = get_akshare()
        if ak is None:
            return 0.0

        try:
            # 尝试多个可能的接口名称（AKShare 版本差异）
            df = None
            try:
                df = ak.stock_hsgt_north_net_flow_in_em()
            except AttributeError:
                pass

            if df is None:
                try:
                    # 备用接口
                    df = ak.stock_em_hsgt_north_net_flow_in()
                except AttributeError:
                    pass

            if df is not None and not df.empty:
                # 取最新一条
                return float(df.iloc[-1].get('当日净流入', 0) or 0)
        except Exception as e:
            print(f"获取北向资金数据失败: {e}")

        return 0.0

    def calculate_capital_flow_features(self, stock_code: str, df: pd.DataFrame = None) -> Dict:
        """
        计算资金流向相关特征

        Args:
            stock_code: 股票代码
            df: 历史行情数据（可选，用于计算成交额占比）

        Returns:
            Dict: 资金流向特征字典
        """
        flow_data = self.get_stock_capital_flow(stock_code)
        north_flow = self.get_north_capital_flow()

        # 计算特征
        total_inflow = abs(flow_data.main_net_inflow) + abs(flow_data.retail_net_inflow)
        main_ratio = flow_data.main_net_inflow / total_inflow if total_inflow > 0 else 0

        features = {
            # 主力资金净流入（万元）
            'main_net_inflow': flow_data.main_net_inflow,

            # 散户资金净流入（万元）
            'retail_net_inflow': flow_data.retail_net_inflow,

            # 主力资金占比（-1 到 1）
            'main_inflow_ratio': main_ratio,

            # 超大单净流入
            'super_large_inflow': flow_data.super_large_inflow,

            # 北向资金净流入（亿元）
            'north_net_inflow': north_flow,

            # 资金流向方向（1=净流入，-1=净流出，0=平衡）
            'capital_flow_direction': 1 if flow_data.main_net_inflow > 0 else (-1 if flow_data.main_net_inflow < 0 else 0),
        }

        return features

    def generate_capital_flow_signal(self, stock_code: str) -> Dict:
        """
        基于资金流向生成交易信号

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 包含 score 和 reasons 的信号字典
        """
        features = self.calculate_capital_flow_features(stock_code)
        score = 0
        reasons = []

        # 主力资金分析
        main_inflow = features['main_net_inflow']
        if main_inflow > 10000:  # 净流入超过1亿
            score += 0.5
            reasons.append(f'主力大幅净流入({main_inflow/10000:.1f}亿)')
        elif main_inflow > 1000:  # 净流入超过1000万
            score += 0.3
            reasons.append(f'主力资金净流入({main_inflow/10000:.2f}亿)')
        elif main_inflow < -10000:  # 净流出超过1亿
            score -= 0.5
            reasons.append(f'主力大幅净流出({abs(main_inflow)/10000:.1f}亿)')
        elif main_inflow < -1000:  # 净流出超过1000万
            score -= 0.3
            reasons.append(f'主力资金净流出({abs(main_inflow)/10000:.2f}亿)')

        # 北向资金分析
        north_flow = features['north_net_inflow']
        if north_flow > 50:  # 净流入超过50亿
            score += 0.3
            reasons.append(f'北向资金大幅流入({north_flow:.0f}亿)')
        elif north_flow > 10:
            score += 0.1
            reasons.append('北向资金净流入')
        elif north_flow < -50:
            score -= 0.3
            reasons.append(f'北向资金大幅流出({abs(north_flow):.0f}亿)')
        elif north_flow < -10:
            score -= 0.1
            reasons.append('北向资金净流出')

        # 主力与散户背离分析
        retail_inflow = features['retail_net_inflow']
        if main_inflow > 0 and retail_inflow < 0:
            score += 0.2
            reasons.append('主力吸筹（散户出逃）')
        elif main_inflow < 0 and retail_inflow > 0:
            score -= 0.2
            reasons.append('主力出货（散户接盘）')

        return {
            'score': float(np.clip(score, -1, 1)),
            'reasons': reasons,
            'features': features
        }


# =============================================================================
# 市场情绪分析器
# =============================================================================
class MarketSentimentAnalyzer:
    """
    市场情绪分析器
    ====================================
    分析整体市场情绪，包括涨跌家数、涨跌停统计等。

    使用示例：
    >>> analyzer = MarketSentimentAnalyzer()
    >>> sentiment = analyzer.get_market_sentiment()
    >>> signal = analyzer.generate_sentiment_signal()
    """

    def __init__(self):
        """初始化市场情绪分析器"""
        self.cache = None
        self.cache_time = None

    def get_market_sentiment(self) -> MarketSentimentData:
        """
        获取市场情绪数据

        Returns:
            MarketSentimentData: 市场情绪数据对象
        """
        # 检查缓存（5分钟有效期）
        if self.cache is not None:
            if datetime.now() - (self.cache_time or datetime.min) < timedelta(minutes=5):
                return self.cache

        ak = get_akshare()
        if ak is None:
            return MarketSentimentData()

        try:
            # 获取涨跌停统计
            limit_up_df = ak.stock_zt_pool_em(date=datetime.now().strftime('%Y%m%d'))
            limit_down_df = ak.stock_zt_pool_dtgc_em(date=datetime.now().strftime('%Y%m%d'))

            limit_up_count = len(limit_up_df) if limit_up_df is not None else 0
            limit_down_count = len(limit_down_df) if limit_down_df is not None else 0

            # 获取市场统计数据
            # 注意：这里使用简化的估算方法
            # 实际可以通过 stock_zh_a_spot_em 获取所有股票实时数据进行统计
            up_count = max(100, limit_up_count * 10)  # 估算值
            down_count = max(100, limit_down_count * 10)  # 估算值
            flat_count = 200  # 估算值

            # 计算涨跌比
            advance_decline_ratio = up_count / down_count if down_count > 0 else 1.0

            # 计算市场强度指数（0-100）
            total = up_count + down_count + flat_count
            market_strength = (up_count / total * 100) if total > 0 else 50

            sentiment_data = MarketSentimentData(
                up_count=up_count,
                down_count=down_count,
                flat_count=flat_count,
                limit_up_count=limit_up_count,
                limit_down_count=limit_down_count,
                advance_decline_ratio=advance_decline_ratio,
                market_strength=market_strength
            )

            # 更新缓存
            self.cache = sentiment_data
            self.cache_time = datetime.now()

            return sentiment_data

        except Exception as e:
            print(f"获取市场情绪数据失败: {e}")

        return MarketSentimentData()

    def calculate_sentiment_features(self) -> Dict:
        """
        计算市场情绪相关特征

        Returns:
            Dict: 市场情绪特征字典
        """
        sentiment = self.get_market_sentiment()

        features = {
            # 涨跌停家数
            'limit_up_count': sentiment.limit_up_count,
            'limit_down_count': sentiment.limit_down_count,

            # 涨跌停比
            'limit_up_down_ratio': sentiment.limit_up_count / max(sentiment.limit_down_count, 1),

            # 涨跌比
            'advance_decline_ratio': sentiment.advance_decline_ratio,

            # 市场强度（0-100）
            'market_strength': sentiment.market_strength,

            # 市场情绪指标（-1 到 1）
            'market_sentiment_score': (sentiment.market_strength - 50) / 50,
        }

        return features

    def generate_sentiment_signal(self) -> Dict:
        """
        基于市场情绪生成交易信号

        Returns:
            Dict: 包含 score 和 reasons 的信号字典
        """
        features = self.calculate_sentiment_features()
        score = 0
        reasons = []

        # 涨跌停分析
        limit_ratio = features['limit_up_down_ratio']
        if limit_ratio > 3:
            score += 0.4
            reasons.append(f'涨停家数远超跌停({features["limit_up_count"]}:{features["limit_down_count"]})')
        elif limit_ratio > 1.5:
            score += 0.2
            reasons.append('涨停家数多于跌停')
        elif limit_ratio < 0.33:
            score -= 0.4
            reasons.append(f'跌停家数远超涨停({features["limit_down_count"]}:{features["limit_up_count"]})')
        elif limit_ratio < 0.67:
            score -= 0.2
            reasons.append('跌停家数多于涨停')

        # 市场强度分析
        strength = features['market_strength']
        if strength > 70:
            score += 0.3
            reasons.append('市场情绪高涨')
        elif strength > 55:
            score += 0.1
            reasons.append('市场偏强')
        elif strength < 30:
            score -= 0.3
            reasons.append('市场情绪低迷')
        elif strength < 45:
            score -= 0.1
            reasons.append('市场偏弱')

        # 涨跌比分析
        ad_ratio = features['advance_decline_ratio']
        if ad_ratio > 2:
            score += 0.2
            reasons.append('上涨家数占优')
        elif ad_ratio < 0.5:
            score -= 0.2
            reasons.append('下跌家数占优')

        return {
            'score': float(np.clip(score, -1, 1)),
            'reasons': reasons,
            'features': features
        }


# =============================================================================
# 增强特征聚合器
# =============================================================================
class EnhancedFeatureGenerator:
    """
    增强特征生成器
    ====================================
    聚合资金流向和市场情绪特征，提供统一的特征接口。

    使用示例：
    >>> generator = EnhancedFeatureGenerator()
    >>> features = generator.generate_all_enhanced_features("000001", df)
    """

    def __init__(self):
        """初始化增强特征生成器"""
        self.capital_flow_analyzer = CapitalFlowAnalyzer()
        self.sentiment_analyzer = MarketSentimentAnalyzer()

    def generate_all_enhanced_features(self, stock_code: str, df: pd.DataFrame = None) -> Dict:
        """
        生成所有增强特征

        Args:
            stock_code: 股票代码
            df: 历史行情数据（可选）

        Returns:
            Dict: 包含资金流向和市场情绪的完整特征字典
        """
        # 获取资金流向特征
        capital_features = self.capital_flow_analyzer.calculate_capital_flow_features(stock_code, df)

        # 获取市场情绪特征
        sentiment_features = self.sentiment_analyzer.calculate_sentiment_features()

        # 合并所有特征
        all_features = {
            **{f'capital_{k}': v for k, v in capital_features.items()},
            **{f'sentiment_{k}': v for k, v in sentiment_features.items()}
        }

        return all_features

    def generate_enhanced_signals(self, stock_code: str) -> Dict:
        """
        生成增强信号

        Args:
            stock_code: 股票代码

        Returns:
            Dict: 包含资金流向信号和市场情绪信号
        """
        capital_signal = self.capital_flow_analyzer.generate_capital_flow_signal(stock_code)
        sentiment_signal = self.sentiment_analyzer.generate_sentiment_signal()

        return {
            'capital_flow': capital_signal,
            'market_sentiment': sentiment_signal
        }
