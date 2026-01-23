"""
ML 配置模块
====================================
集中管理机器学习相关的所有配置参数，便于调试和维护。

本模块包含以下配置：
- 特征工程参数
- 模型训练参数
- 信号生成参数
- 风险评估参数
"""
from typing import Dict, List
from dataclasses import dataclass, field


# =============================================================================
# 特征工程配置
# =============================================================================
@dataclass
class FeatureConfig:
    """
    特征工程配置类

    Attributes:
        windows: 回看窗口列表，用于计算各类滚动特征
        ma_periods: 移动平均周期列表
        include_technical: 是否包含技术指标特征
        nan_fill_value: NaN 填充值
    """
    # 默认回看窗口：5日、10日、20日、60日
    windows: List[int] = field(default_factory=lambda: [5, 10, 20, 60])

    # 移动平均周期
    ma_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60])

    # 是否包含技术指标特征（MACD、RSI、KDJ、BOLL等）
    include_technical: bool = True

    # NaN 填充值
    nan_fill_value: float = 0.0


# =============================================================================
# 模型训练配置
# =============================================================================
@dataclass
class ModelConfig:
    """
    模型训练配置类

    Attributes:
        forward_days: 预测未来天数
        train_ratio: 训练集比例
        threshold: 方向判断阈值
        num_boost_round: 最大迭代次数
        early_stopping_rounds: 早停轮数
    """
    # 预测周期（天）
    forward_days: int = 5

    # 训练集比例
    train_ratio: float = 0.8

    # 方向判断阈值（0表示纯涨跌，>0表示需要超过阈值才算涨）
    threshold: float = 0.0

    # 最大迭代次数
    num_boost_round: int = 500

    # 早停轮数
    early_stopping_rounds: int = 50


# =============================================================================
# LightGBM 模型参数
# =============================================================================
LIGHTGBM_PARAMS: Dict = {
    # 目标函数：二分类
    'objective': 'binary',

    # 评估指标：AUC
    'metric': 'auc',

    # 提升类型：梯度提升决策树
    'boosting_type': 'gbdt',

    # 叶子节点数量（控制模型复杂度）
    'num_leaves': 31,

    # 学习率
    'learning_rate': 0.05,

    # 特征采样比例（每次迭代使用80%特征）
    'feature_fraction': 0.8,

    # 数据采样比例
    'bagging_fraction': 0.8,

    # 采样频率
    'bagging_freq': 5,

    # 叶子节点最小样本数
    'min_child_samples': 20,

    # 日志级别（-1表示静默）
    'verbose': -1,

    # 并行线程数（-1表示使用所有可用核心）
    'n_jobs': -1,

    # 随机种子
    'seed': 42
}


# =============================================================================
# 分位数回归参数
# =============================================================================
QUANTILE_PARAMS: Dict = {
    # 目标函数：分位数回归
    'objective': 'quantile',

    # 提升类型
    'boosting_type': 'gbdt',

    # 叶子节点数量
    'num_leaves': 31,

    # 学习率
    'learning_rate': 0.05,

    # 特征采样比例
    'feature_fraction': 0.8,

    # 日志级别
    'verbose': -1,

    # 并行线程数
    'n_jobs': -1,

    # 随机种子
    'seed': 42
}


# =============================================================================
# 信号生成配置
# =============================================================================
@dataclass
class SignalConfig:
    """
    信号生成配置类

    Attributes:
        risk_tolerance: 风险偏好级别
        holding_period: 预期持仓周期
        min_data_days: 最小数据天数
    """
    # 风险偏好：conservative（保守）、moderate（中等）、aggressive（激进）
    risk_tolerance: str = 'moderate'

    # 预期持仓周期（天）
    holding_period: int = 5

    # 最小数据天数要求
    min_data_days: int = 60


# =============================================================================
# 风险参数配置
# =============================================================================
RISK_PARAMS: Dict[str, Dict] = {
    # 保守型配置
    'conservative': {
        'signal_threshold': 0.6,       # 信号阈值（需要更强信号才触发）
        'stop_loss_atr_mult': 1.5,     # 止损 ATR 倍数
        'take_profit_atr_mult': 2.0,   # 止盈 ATR 倍数
        'min_confidence': 0.6          # 最小置信度要求
    },

    # 稳健型配置
    'moderate': {
        'signal_threshold': 0.4,
        'stop_loss_atr_mult': 2.0,
        'take_profit_atr_mult': 3.0,
        'min_confidence': 0.4
    },

    # 激进型配置
    'aggressive': {
        'signal_threshold': 0.2,
        'stop_loss_atr_mult': 2.5,
        'take_profit_atr_mult': 4.0,
        'min_confidence': 0.2
    }
}


# =============================================================================
# 信号权重配置（各分析维度的权重分配）
# =============================================================================
SIGNAL_WEIGHTS: Dict[str, float] = {
    # 技术指标分析权重
    'technical': 0.25,

    # 趋势分析权重
    'trend': 0.20,

    # 动量分析权重
    'momentum': 0.15,

    # 波动率分析权重
    'volatility': 0.10,

    # 成交量分析权重
    'volume': 0.05,

    # 资金流向权重（新增）
    'capital_flow': 0.15,

    # 市场情绪权重（新增）
    'market_sentiment': 0.10
}


# =============================================================================
# 波动率阈值配置
# =============================================================================
VOLATILITY_THRESHOLDS: Dict[str, float] = {
    # 高波动率阈值（年化）
    'high': 0.40,

    # 中波动率阈值（年化）
    'medium': 0.20,

    # 低波动率阈值（年化）
    'low': 0.10
}


# =============================================================================
# 价格区间预测配置
# =============================================================================
@dataclass
class PriceRangeConfig:
    """
    价格区间预测配置

    Attributes:
        quantiles: 预测的分位数列表
        confidence_levels: 置信水平列表
    """
    # 分位数列表
    quantiles: List[float] = field(default_factory=lambda: [0.1, 0.25, 0.5, 0.75, 0.9])

    # 置信水平列表（用于基于波动率的区间预测）
    confidence_levels: List[float] = field(default_factory=lambda: [0.68, 0.95])


# =============================================================================
# 全局配置实例
# =============================================================================
# 特征工程默认配置
DEFAULT_FEATURE_CONFIG = FeatureConfig()

# 模型训练默认配置
DEFAULT_MODEL_CONFIG = ModelConfig()

# 信号生成默认配置
DEFAULT_SIGNAL_CONFIG = SignalConfig()

# 价格区间预测默认配置
DEFAULT_PRICE_RANGE_CONFIG = PriceRangeConfig()
