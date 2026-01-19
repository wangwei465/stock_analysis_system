# 智能预测 API 文档

股票分析系统智能预测(ML)模块详细参数说明与使用示例。

## 目录

- [1. 价格方向预测](#1-价格方向预测)
- [2. 价格区间预测](#2-价格区间预测)
- [3. 价格目标位预测](#3-价格目标位预测)
- [4. 交易信号](#4-交易信号)
- [5. 综合预测](#5-综合预测)
- [6. 个股情感分析](#6-个股情感分析)
- [7. 市场情感分析](#7-市场情感分析)

---

## 1. 价格方向预测

**接口地址：** `GET /api/v1/ml/direction/{code}`

**功能说明：** 基于多维度技术指标综合分析，预测股票未来价格走势方向。

### 请求参数

| 参数名 | 类型 | 位置 | 必需 | 默认值 | 说明 |
|--------|------|------|------|--------|------|
| code | string | path | 是 | - | 股票代码，如 `000001`、`600519` |
| days | int | query | 否 | 5 | 预测天数，范围 1-30 |

### 返回参数

```json
{
  "stock_code": "000001",
  "forward_days": 5,
  "prediction": {
    "direction": 1,
    "direction_label": "看涨",
    "confidence": 0.85,
    "score": 0.72,
    "signals": {
      "ma_trend": "多头排列",
      "rsi": "偏强",
      "macd": "红柱增长",
      "kdj": "金叉",
      "volume": "放量"
    }
  }
}
```

### 参数详解

| 字段 | 类型 | 取值范围 | 说明 |
|------|------|----------|------|
| stock_code | string | - | 请求的股票代码 |
| forward_days | int | 1-30 | 预测的天数 |
| prediction.direction | int | -1, 0, 1 | 方向：-1=看跌，0=震荡，1=看涨 |
| prediction.direction_label | string | 看跌/震荡/看涨 | 方向的中文描述 |
| prediction.confidence | float | 0.0-1.0 | 置信度，越接近1表示预测越可靠 |
| prediction.score | float | -1.0 to 1.0 | 综合评分，负值偏空，正值偏多 |

### signals 信号说明

| 信号 | 可能值 | 说明 |
|------|--------|------|
| ma_trend | 多头排列 / 空头排列 | MA5 与 MA20 的关系，多头=MA5>MA20 |
| rsi | 超买 / 超卖 / 偏强 / 偏弱 | RSI(14) 指标状态，>70超买，<30超卖 |
| macd | 红柱增长 / 红柱缩短 / 绿柱增长 / 绿柱缩短 | MACD 柱状图变化趋势 |
| kdj | 金叉 / 死叉 / 超买区 / 超卖区 / 中性 | KDJ 指标状态 |
| volume | 放量 / 缩量 / 平量 | 成交量与20日均量对比 |

### 示例

**请求：**
```
GET /api/v1/ml/direction/000001?days=5
```

**响应解读：**
- `direction: 1` + `direction_label: "看涨"` → 预测未来5天股价上涨
- `confidence: 0.85` → 85%的置信度，可信度较高
- `score: 0.72` → 综合得分偏多，多项指标支持上涨判断
- `signals.ma_trend: "多头排列"` → 短期均线在长期均线上方，趋势向上
- `signals.macd: "红柱增长"` → MACD红柱持续放大，动能增强

---

## 2. 价格区间预测

**接口地址：** `GET /api/v1/ml/price-range/{code}`

**功能说明：** 基于历史波动率统计，预测未来价格可能的波动区间。

### 请求参数

| 参数名 | 类型 | 位置 | 必需 | 默认值 | 说明 |
|--------|------|------|------|--------|------|
| code | string | path | 是 | - | 股票代码 |
| days | int | query | 否 | 5 | 预测天数，范围 1-30 |

### 返回参数

```json
{
  "stock_code": "000001",
  "prediction": {
    "current_price": 12.50,
    "forward_days": 5,
    "volatility": {
      "daily": 1.5,
      "annualized": 23.8,
      "forward_period": 3.35,
      "vol_5d": 1.2,
      "vol_20d": 1.8
    },
    "price_ranges": [
      {
        "confidence": 0.68,
        "lower": 12.08,
        "upper": 12.92,
        "range_pct": 6.72
      },
      {
        "confidence": 0.95,
        "lower": 11.67,
        "upper": 13.33,
        "range_pct": 13.28
      }
    ],
    "expected": {
      "price": 12.65,
      "return_pct": 1.2
    },
    "support_resistance": {
      "resistance": 13.20,
      "support": 11.80,
      "atr_14": 0.35
    },
    "risk_assessment": {
      "atr_pct": 2.8,
      "volatility_level": "中"
    }
  }
}
```

### 参数详解

#### volatility 波动率

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| daily | float | % | 日波动率，基于收益率标准差计算 |
| annualized | float | % | 年化波动率 = 日波动率 × √252 |
| forward_period | float | % | 预测期间波动率 = 日波动率 × √预测天数 |
| vol_5d | float | % | 近5日波动率 |
| vol_20d | float | % | 近20日波动率 |

#### price_ranges 价格区间

| 字段 | 类型 | 说明 |
|------|------|------|
| confidence | float | 置信水平：0.68(68%) 或 0.95(95%) |
| lower | float | 预测价格下限 |
| upper | float | 预测价格上限 |
| range_pct | float | 区间幅度百分比 |

**置信水平解读：**
- **68% 置信区间：** 有 68% 的概率价格会落在此区间内（约1个标准差）
- **95% 置信区间：** 有 95% 的概率价格会落在此区间内（约2个标准差）

#### expected 预期价格

| 字段 | 类型 | 说明 |
|------|------|------|
| price | float | 基于趋势的预期价格 |
| return_pct | float | 预期收益率(%) |

#### support_resistance 支撑阻力

| 字段 | 类型 | 说明 |
|------|------|------|
| resistance | float | 阻力位（近20日最高价） |
| support | float | 支撑位（近20日最低价） |
| atr_14 | float | 14期真实波动幅度(ATR) |

#### risk_assessment 风险评估

| 字段 | 类型 | 说明 |
|------|------|------|
| atr_pct | float | ATR占现价的百分比 |
| volatility_level | string | 波动率等级：低/中/高 |

### 示例

**请求：**
```
GET /api/v1/ml/price-range/600519?days=10
```

**响应解读：**
- `current_price: 12.50` → 当前股价 12.50 元
- `price_ranges[0]` → 68%概率下，10天后价格在 12.08-12.92 之间
- `price_ranges[1]` → 95%概率下，10天后价格在 11.67-13.33 之间
- `expected.price: 12.65` → 基于趋势预测，预期价格 12.65 元
- `support_resistance.support: 11.80` → 支撑位 11.80，跌破需警惕
- `risk_assessment.volatility_level: "中"` → 波动风险中等

---

## 3. 价格目标位预测

**接口地址：** `GET /api/v1/ml/price-target/{code}`

**功能说明：** 结合技术分析计算多种目标价位，包括看涨/看跌目标和斐波那契回撤位。

### 请求参数

| 参数名 | 类型 | 位置 | 必需 | 默认值 | 说明 |
|--------|------|------|------|--------|------|
| code | string | path | 是 | - | 股票代码 |
| days | int | query | 否 | 20 | 目标周期，范围 5-60 |

### 返回参数

```json
{
  "stock_code": "000001",
  "prediction": {
    "current_price": 12.50,
    "forward_days": 20,
    "targets": {
      "bullish": {
        "conservative": 13.20,
        "moderate": 13.80,
        "aggressive": 14.50
      },
      "bearish": {
        "conservative": 11.80,
        "moderate": 11.20,
        "aggressive": 10.50
      },
      "trend_based": 13.10
    },
    "technical_levels": {
      "boll_upper": 13.50,
      "boll_lower": 11.50,
      "ma5": 12.45,
      "ma10": 12.38,
      "ma20": 12.30,
      "ma60": 12.10,
      "high_52w": 15.80,
      "low_52w": 10.20
    },
    "fibonacci": {
      "0": 10.20,
      "0.236": 11.52,
      "0.382": 12.34,
      "0.5": 13.00,
      "0.618": 13.66,
      "0.786": 14.60,
      "1": 15.80
    },
    "trend": {
      "slope": 0.05,
      "direction": "上升",
      "strength": 0.04
    }
  }
}
```

### 参数详解

#### targets 目标价位

| 字段 | 说明 |
|------|------|
| bullish.conservative | 保守看涨目标（基于布林带上轨） |
| bullish.moderate | 中等看涨目标（基于斐波那契0.618） |
| bullish.aggressive | 激进看涨目标（基于52周高点） |
| bearish.conservative | 保守看跌目标（基于布林带下轨） |
| bearish.moderate | 中等看跌目标（基于斐波那契0.382） |
| bearish.aggressive | 激进看跌目标（基于52周低点） |
| trend_based | 基于线性回归趋势的目标价 |

#### technical_levels 技术位

| 字段 | 说明 |
|------|------|
| boll_upper | 布林带上轨（20日均线+2倍标准差） |
| boll_lower | 布林带下轨（20日均线-2倍标准差） |
| ma5/ma10/ma20/ma60 | 各周期移动平均线 |
| high_52w | 52周最高价 |
| low_52w | 52周最低价 |

#### fibonacci 斐波那契回撤位

基于52周高低点计算的关键回撤位：

| 回撤比例 | 含义 |
|----------|------|
| 0 | 52周低点（0%回撤） |
| 0.236 | 23.6%回撤位 |
| 0.382 | 38.2%回撤位（重要支撑/阻力） |
| 0.5 | 50%回撤位（中间位） |
| 0.618 | 61.8%回撤位（黄金分割，最重要） |
| 0.786 | 78.6%回撤位 |
| 1 | 52周高点（100%回撤） |

#### trend 趋势信息

| 字段 | 类型 | 说明 |
|------|------|------|
| slope | float | 线性回归斜率（每日价格变化） |
| direction | string | 趋势方向：上升/下降 |
| strength | float | 趋势强度（斜率/现价的比例） |

### 示例

**请求：**
```
GET /api/v1/ml/price-target/000001?days=20
```

**响应解读：**
- 当前价格 12.50 元
- **看涨情景：**
  - 保守目标 13.20（+5.6%），到达布林带上轨
  - 中等目标 13.80（+10.4%），到达斐波那契 0.618 位
  - 激进目标 14.50（+16%），接近历史高点
- **看跌情景：**
  - 保守目标 11.80（-5.6%），到达布林带下轨
  - 中等目标 11.20（-10.4%），到达斐波那契 0.382 位
- `fibonacci["0.618"]: 13.66` → 黄金分割位 13.66，重要阻力位
- `trend.direction: "上升"` → 当前处于上升趋势

---

## 4. 交易信号

**接口地址：** `GET /api/v1/ml/signal/{code}`

**功能说明：** 生成综合交易信号，包含建议的入场价、止损位、止盈位。

### 请求参数

| 参数名 | 类型 | 位置 | 必需 | 默认值 | 说明 |
|--------|------|------|------|--------|------|
| code | string | path | 是 | - | 股票代码 |
| risk_tolerance | string | query | 否 | moderate | 风险偏好：conservative/moderate/aggressive |
| holding_period | int | query | 否 | 5 | 预期持仓周期（天），范围 1-30 |

### 风险偏好参数

| 风险偏好 | 信号阈值 | 止损倍数 | 止盈倍数 | 最低置信度 |
|----------|----------|----------|----------|------------|
| conservative（保守）| 0.6 | 1.5×ATR | 2.0×ATR | 0.6 |
| moderate（稳健）| 0.4 | 2.0×ATR | 3.0×ATR | 0.4 |
| aggressive（激进）| 0.2 | 2.5×ATR | 4.0×ATR | 0.2 |

### 返回参数

```json
{
  "stock_code": "000001",
  "stock_name": "平安银行",
  "signal": {
    "signal": 1,
    "signal_label": "买入",
    "confidence": 0.75,
    "score": 0.55,
    "reasons": [
      "RSI低位回升(32.5)",
      "MACD金叉",
      "均线多头排列"
    ],
    "entry_price": 12.50,
    "stop_loss": 11.80,
    "take_profit": 13.55,
    "risk_reward_ratio": 1.5,
    "atr": 0.35,
    "risk_tolerance": "moderate",
    "holding_period": 5,
    "components": {
      "technical": {
        "score": 0.30,
        "reasons": ["RSI低位回升(32.5)", "MACD金叉"]
      },
      "trend": {
        "score": 0.25,
        "reasons": ["均线多头排列", "价格站上MA20"]
      },
      "momentum": {
        "score": 0.15,
        "reasons": ["5日涨幅2.3%"]
      },
      "volatility": {
        "score": 0.08,
        "reasons": ["波动率下降"]
      },
      "volume": {
        "score": 0.12,
        "reasons": ["放量上涨(量比1.8)"]
      }
    }
  }
}
```

### 参数详解

#### signal 主信号

| 字段 | 类型 | 取值 | 说明 |
|------|------|------|------|
| signal | int | -2, -1, 0, 1, 2 | 信号强度 |
| signal_label | string | - | 信号标签 |

**信号对照表：**

| signal值 | signal_label | 含义 | 建议操作 |
|----------|--------------|------|----------|
| 2 | 强烈买入 | 多重指标共振看涨 | 可较大仓位买入 |
| 1 | 买入 | 主要指标看涨 | 可适量买入 |
| 0 | 持有/观望 | 方向不明确 | 暂不操作 |
| -1 | 卖出 | 主要指标看跌 | 可适量卖出 |
| -2 | 强烈卖出 | 多重指标共振看跌 | 建议清仓或大幅减仓 |

#### 交易建议参数

| 字段 | 类型 | 说明 |
|------|------|------|
| entry_price | float | 建议入场价（当前价格） |
| stop_loss | float | 建议止损价（仅买入/卖出信号时有值） |
| take_profit | float | 建议止盈价（仅买入/卖出信号时有值） |
| risk_reward_ratio | float | 风险收益比 = 预期盈利 / 预期亏损 |
| atr | float | 14期平均真实波动幅度 |

#### components 信号组成

各维度对综合信号的贡献：

| 维度 | 权重 | 分析内容 |
|------|------|----------|
| technical | 30% | RSI、MACD、KDJ、布林带等技术指标 |
| trend | 25% | 均线系统、价格与均线关系、趋势方向 |
| momentum | 20% | 5日/20日收益率、ROC动量指标 |
| volatility | 15% | 波动率变化、波动率水平 |
| volume | 10% | 量比、价量配合、放量/缩量 |

### 示例

**请求：**
```
GET /api/v1/ml/signal/000001?risk_tolerance=moderate&holding_period=5
```

**响应解读：**
- `signal: 1` + `signal_label: "买入"` → 建议买入
- `confidence: 0.75` → 75%置信度，信号较可靠
- `entry_price: 12.50` → 建议在 12.50 元入场
- `stop_loss: 11.80` → 止损设在 11.80 元，亏损 5.6%
- `take_profit: 13.55` → 止盈设在 13.55 元，盈利 8.4%
- `risk_reward_ratio: 1.5` → 风险收益比 1:1.5，预期收益大于风险
- `reasons` → 买入理由：RSI低位回升、MACD金叉、均线多头排列

---

## 5. 综合预测

**接口地址：** `GET /api/v1/ml/comprehensive/{code}`

**功能说明：** 整合方向预测、价格区间、交易信号、风险评估和情感分析的综合报告。

### 请求参数

| 参数名 | 类型 | 位置 | 必需 | 默认值 | 说明 |
|--------|------|------|------|--------|------|
| code | string | path | 是 | - | 股票代码 |
| forward_days | int | query | 否 | 5 | 预测天数，范围 1-30 |
| include_sentiment | bool | query | 否 | true | 是否包含情感分析 |

### 返回参数

```json
{
  "stock_code": "000001",
  "stock_name": "平安银行",
  "forward_days": 5,
  "prediction_date": "2024-01-19",
  "stock_info": {
    "current_price": 12.50,
    "date": "2024-01-19"
  },
  "direction": { ... },
  "price_range": { ... },
  "signal": { ... },
  "risk": {
    "daily_volatility": 1.5,
    "annualized_volatility": 23.8,
    "max_drawdown_20d": -5.2,
    "var_95": -2.8,
    "cvar_95": -3.5
  },
  "recommendation": {
    "action": "适度买入",
    "risk_level": "中等",
    "score": 0.45,
    "summary": "买入 - 看涨"
  },
  "sentiment": { ... }
}
```

### 参数详解

#### risk 风险指标

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| daily_volatility | float | % | 日波动率 |
| annualized_volatility | float | % | 年化波动率 |
| max_drawdown_20d | float | % | 近20日最大回撤（负值） |
| var_95 | float | % | 95%风险价值(VaR)：在95%置信度下，单日最大可能亏损 |
| cvar_95 | float | % | 条件风险价值(CVaR)：超过VaR时的平均损失 |

**VaR/CVaR 解读示例：**
- `var_95: -2.8` → 有5%的概率单日亏损超过2.8%
- `cvar_95: -3.5` → 当亏损超过VaR时，平均会亏损3.5%

#### recommendation 综合建议

| 字段 | 类型 | 说明 |
|------|------|------|
| action | string | 建议操作 |
| risk_level | string | 风险等级 |
| score | float | 综合评分(0-1) |
| summary | string | 摘要 |

**action 可能值：**

| 值 | 触发条件 | 说明 |
|------|----------|------|
| 积极买入 | score >= 0.6 | 强烈看多信号 |
| 适度买入 | 0.3 <= score < 0.6 | 偏多信号 |
| 观望 | -0.3 < score < 0.3 | 方向不明 |
| 减仓 | -0.6 < score <= -0.3 | 偏空信号 |
| 建议卖出 | score <= -0.6 | 强烈看空信号 |

**risk_level 可能值：**

| 值 | 年化波动率范围 | 说明 |
|------|----------------|------|
| 低 | < 20% | 波动较小，风险可控 |
| 较低 | 20%-30% | 波动适中 |
| 中等 | 30%-40% | 波动较大 |
| 较高 | > 40% | 高波动，高风险 |

### 示例

**请求：**
```
GET /api/v1/ml/comprehensive/000001?forward_days=5&include_sentiment=true
```

**响应解读：**
- `direction.direction_label: "看涨"` → 方向预测看涨
- `price_range.price_ranges[0]` → 68%概率下的价格区间
- `signal.signal_label: "买入"` → 交易信号建议买入
- `risk.var_95: -2.8` → 单日最大可能亏损2.8%
- `recommendation.action: "适度买入"` → 综合建议适度买入
- `recommendation.risk_level: "中等"` → 风险等级中等

---

## 6. 个股情感分析

**接口地址：** `GET /api/v1/ml/sentiment/{code}`

**功能说明：** 爬取个股相关新闻，进行中文情感分析，判断市场情绪。

### 请求参数

| 参数名 | 类型 | 位置 | 必需 | 默认值 | 说明 |
|--------|------|------|------|--------|------|
| code | string | path | 是 | - | 股票代码 |
| limit | int | query | 否 | 20 | 新闻数量，范围 5-50 |

### 返回参数

```json
{
  "stock_code": "000001",
  "stock_sentiment": {
    "score": 0.35,
    "label": "整体积极",
    "news_count": 15
  },
  "market_sentiment": {
    "score": 0.20,
    "label": "整体中性",
    "news_count": 15
  },
  "combined": {
    "score": 0.305,
    "label": "看涨情绪",
    "color": "green"
  },
  "recommendation": "市场情绪偏向积极，可关注潜在机会",
  "top_news": [
    {
      "title": "平安银行一季度净利润同比增长15%",
      "source": "财联社",
      "publish_time": "2024-01-19 10:30",
      "sentiment": {
        "score": 0.65,
        "label": "非常积极",
        "level": 2,
        "positive_words": ["增长", "利润", "超预期"],
        "negative_words": []
      }
    }
  ],
  "status": "success"
}
```

### 参数详解

#### stock_sentiment 个股情感

| 字段 | 类型 | 说明 |
|------|------|------|
| score | float | 个股新闻情感得分，-1到1 |
| label | string | 整体情感标签 |
| news_count | int | 分析的新闻数量 |

#### market_sentiment 市场情感

| 字段 | 类型 | 说明 |
|------|------|------|
| score | float | 市场新闻情感得分，-1到1 |
| label | string | 整体情感标签 |
| news_count | int | 分析的新闻数量 |

#### combined 综合情感

| 字段 | 类型 | 说明 |
|------|------|------|
| score | float | 综合得分 = 70%×个股 + 30%×市场 |
| label | string | 综合情感标签：看涨情绪/情绪中性/看跌情绪 |
| color | string | 颜色编码：green/gray/red |

#### 情感分数对照表

| 分数范围 | label | level | 说明 |
|----------|-------|-------|------|
| >= 0.5 | 非常积极 | 2 | 强烈正面 |
| 0.2 ~ 0.5 | 积极 | 1 | 偏正面 |
| -0.2 ~ 0.2 | 中性 | 0 | 中立 |
| -0.5 ~ -0.2 | 消极 | -1 | 偏负面 |
| < -0.5 | 非常消极 | -2 | 强烈负面 |

#### recommendation 建议

基于综合情感分数的建议：

| 综合分数 | 建议内容 |
|----------|----------|
| >= 0.5 | 市场情绪非常乐观，利好消息较多，但需注意追高风险 |
| 0.2 ~ 0.5 | 市场情绪偏向积极，可关注潜在机会 |
| -0.2 ~ 0.2 | 市场情绪中性，建议观望等待明确方向 |
| -0.5 ~ -0.2 | 市场情绪偏向消极，注意风险控制 |
| < -0.5 | 市场情绪非常悲观，利空消息较多，建议谨慎操作 |

#### top_news 新闻详情

| 字段 | 类型 | 说明 |
|------|------|------|
| title | string | 新闻标题 |
| source | string | 新闻来源 |
| publish_time | string | 发布时间 |
| sentiment.score | float | 该条新闻的情感得分 |
| sentiment.label | string | 情感标签 |
| sentiment.level | int | 情感级别(-2到2) |
| sentiment.positive_words | array | 检测到的积极词汇 |
| sentiment.negative_words | array | 检测到的消极词汇 |

### 示例

**请求：**
```
GET /api/v1/ml/sentiment/000001?limit=20
```

**响应解读：**
- `stock_sentiment.score: 0.35` → 个股新闻整体偏积极
- `market_sentiment.score: 0.20` → 市场整体情绪中性偏多
- `combined.score: 0.305` → 综合情感得分 0.305
- `combined.label: "看涨情绪"` → 综合判断为看涨情绪
- `combined.color: "green"` → 显示为绿色（积极）
- `top_news[0].sentiment.positive_words` → 第一条新闻包含"增长"、"利润"等积极词汇

---

## 7. 市场情感分析

**接口地址：** `GET /api/v1/ml/sentiment/market`

**功能说明：** 分析整体市场新闻情感，了解市场整体情绪。

### 请求参数

| 参数名 | 类型 | 位置 | 必需 | 默认值 | 说明 |
|--------|------|------|------|--------|------|
| limit | int | query | 否 | 30 | 新闻数量，范围 10-50 |

### 返回参数

```json
{
  "overall_score": 0.25,
  "overall_label": "整体积极",
  "news_count": 30,
  "positive_count": 12,
  "negative_count": 8,
  "neutral_count": 10,
  "sentiment_distribution": {
    "positive": 40.0,
    "negative": 26.67,
    "neutral": 33.33
  },
  "analyzed_news": [
    {
      "title": "A股三大指数集体收涨",
      "source": "证券时报",
      "publish_time": "2024-01-19 15:30",
      "sentiment": {
        "score": 0.55,
        "label": "非常积极",
        "level": 2,
        "positive_words": ["收涨", "上涨", "反弹"],
        "negative_words": []
      }
    }
  ],
  "status": "success"
}
```

### 参数详解

| 字段 | 类型 | 说明 |
|------|------|------|
| overall_score | float | 市场整体情感得分，-1到1 |
| overall_label | string | 整体情感标签 |
| news_count | int | 分析的新闻总数 |
| positive_count | int | 积极新闻数量（score > 0.2） |
| negative_count | int | 消极新闻数量（score < -0.2） |
| neutral_count | int | 中性新闻数量 |
| sentiment_distribution | object | 情感分布百分比 |
| analyzed_news | array | 前10条分析过的新闻详情 |

### overall_label 判断标准

| 分数范围 | overall_label |
|----------|---------------|
| >= 0.3 | 整体积极 |
| <= -0.3 | 整体消极 |
| -0.3 ~ 0.3 | 整体中性 |

### 示例

**请求：**
```
GET /api/v1/ml/sentiment/market?limit=30
```

**响应解读：**
- `overall_score: 0.25` → 市场整体情感偏正面
- `overall_label: "整体积极"` → 整体判断为积极
- `positive_count: 12` → 30条新闻中12条为正面
- `negative_count: 8` → 8条为负面
- `sentiment_distribution.positive: 40.0` → 40%的新闻为正面

---

## 附录

### A. 情感分析词汇表

#### 积极词汇（部分）

| 类别 | 词汇示例 |
|------|----------|
| 价格相关 | 涨、上涨、涨停、大涨、反弹、突破、创新高 |
| 业绩相关 | 增长、盈利、利润、超预期、业绩翻番 |
| 资金相关 | 买入、增持、加仓、抄底、资金流入 |
| 评级相关 | 利好、看好、推荐、强烈推荐 |

#### 消极词汇（部分）

| 类别 | 词汇示例 |
|------|----------|
| 价格相关 | 跌、下跌、跌停、大跌、暴跌、破位、创新低 |
| 业绩相关 | 亏损、下滑、业绩不及预期、营收下降 |
| 资金相关 | 卖出、减持、清仓、资金流出、抛售 |
| 风险相关 | 利空、风险、警示、退市、违规 |

#### 程度副词

| 程度 | 词汇 | 权重倍数 |
|------|------|----------|
| 强 | 非常、极其、巨幅、暴 | 2.0 |
| 中 | 较、比较、相当 | 1.5 |
| 弱 | 略、稍、小幅 | 1.2 |

#### 否定词

否定词会反转后续词汇的情感方向：
- 不、没、无、未、非、否

### B. 数据要求

| API | 最少历史数据 |
|-----|-------------|
| 方向预测 | 60天 |
| 价格区间 | 60天 |
| 价格目标 | 120天 |
| 交易信号 | 60天 |
| 综合预测 | 60天 |

### C. 错误响应

当数据不足或请求异常时：

```json
{
  "detail": "数据不足，需要至少60天的历史数据"
}
```

| HTTP状态码 | 说明 |
|------------|------|
| 400 | 数据不足或参数错误 |
| 500 | 服务器内部错误 |
