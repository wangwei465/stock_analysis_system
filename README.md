# A股股票分析系统

基于 FastAPI + React 的 A股股票分析系统，支持K线图表、技术指标、选股筛选、策略回测和智能预测。

## 功能特性

### 已完成（阶段一）
- ✅ K线图表展示（日K/周K/月K）
- ✅ 技术指标：MA、MACD、RSI、KDJ、BOLL
- ✅ 实时行情数据
- ✅ 股票搜索

### 已完成（阶段二）
- ✅ WebSocket实时行情推送
- ✅ 基本面数据（公司概况、财务报表、估值指标）
- ✅ 多条件选股筛选器（支持5种预设策略）
- ✅ 投资组合管理（创建组合、添加持仓、盈亏计算）
- ✅ 数据可视化仪表盘（涨跌榜、放量异动）

### 已完成（阶段三）
- ✅ 策略回测引擎（支持手续费、滑点模拟）
- ✅ 7种内置量化策略（MA交叉、双均线、MACD、RSI、KDJ、布林带等）
- ✅ 完整绩效指标（收益率、夏普比率、最大回撤、胜率等）
- ✅ 权益曲线可视化
- ✅ 交易记录详情

### 已完成（阶段四）
- ✅ ML特征工程（价格特征、动量特征、波动率特征、技术指标特征）
- ✅ 价格方向预测（基于技术指标的快速预测模型）
- ✅ 价格区间预测（基于历史波动率估算）
- ✅ 综合交易信号（多维度信号生成器）
- ✅ 情感分析（新闻爬取、中文情感分析）
- ✅ 风险评估（VaR、CVaR、波动率分析）

## 内置策略

| 策略ID | 名称 | 说明 |
|--------|------|------|
| ma_cross | MA交叉策略 | 快速均线上穿慢速均线买入，下穿卖出 |
| double_ma | 双均线趋势策略 | 在长期均线上方时才执行金叉买入 |
| macd | MACD策略 | MACD金叉买入，死叉卖出 |
| macd_hist | MACD柱状图策略 | 柱状图由负转正买入，由正转负卖出 |
| rsi | RSI超买超卖策略 | RSI超卖区向上突破买入，超买区向下突破卖出 |
| kdj | KDJ金叉死叉策略 | KDJ低位金叉买入，高位死叉卖出 |
| bollinger | 布林带均值回归策略 | 价格触及下轨买入，触及上轨卖出 |

## 智能预测功能

### 方向预测
基于多维度技术指标综合分析：
- 趋势信号（均线系统、线性回归）
- 动量信号（RSI、MACD、KDJ）
- 波动率信号（ATR、布林带）
- 成交量信号（量价配合分析）

### 价格区间预测
- 基于历史波动率的统计预测
- 多置信水平区间估算（68%、95%）
- 支撑位/阻力位识别
- 斐波那契回撤分析

### 交易信号
| 信号 | 含义 |
|------|------|
| 强烈买入 | 多重指标共振看涨 |
| 买入 | 主要指标看涨 |
| 持有/观望 | 方向不明确 |
| 卖出 | 主要指标看跌 |
| 强烈卖出 | 多重指标共振看跌 |

### 情感分析
- 个股新闻情感分析
- 市场整体情绪监测
- 积极/消极词汇识别
- 综合情绪评分

## 技术栈

### 后端
- FastAPI - Web框架
- SQLModel - ORM
- AKShare - A股数据源
- Pandas/NumPy - 数据处理
- LightGBM - 机器学习（可选）
- Scikit-learn - 数据科学工具

### 前端
- React 18 + TypeScript
- Vite - 构建工具
- Lightweight Charts - K线图表
- Ant Design - UI组件
- Zustand - 状态管理

## 快速开始

### Windows 一键启动

```bash
# 首次运行 - 安装依赖
双击 install.bat

# 启动系统
双击 start.bat

# 停止服务
双击 stop.bat
```

| 脚本 | 说明 |
|------|------|
| `install.bat` | 首次安装 - 创建虚拟环境、安装依赖 |
| `start.bat` | 一键启动 - 同时启动前后端，自动打开浏览器 |
| `stop.bat` | 停止所有服务 |
| `start-backend.bat` | 仅启动后端服务 |
| `start-frontend.bat` | 仅启动前端服务 |

### 手动启动

#### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 2. 启动后端服务

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端API文档：http://localhost:8000/docs

#### 3. 安装前端依赖

```bash
cd frontend
npm install
```

#### 4. 启动前端服务

```bash
cd frontend
npm run dev
```

前端访问：http://localhost:5173

## 项目结构

```
├── backend/                 # Python后端
│   ├── app/
│   │   ├── main.py         # FastAPI入口
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库
│   │   ├── api/v1/         # API路由
│   │   │   ├── stocks.py       # 股票数据API
│   │   │   ├── indicators.py   # 技术指标API
│   │   │   ├── fundamental.py  # 基本面API
│   │   │   ├── screener.py     # 选股筛选API
│   │   │   ├── portfolio.py    # 投资组合API
│   │   │   ├── backtest.py     # 回测API
│   │   │   ├── ml.py           # ML预测API
│   │   │   └── websocket.py    # WebSocket API
│   │   ├── core/           # 核心业务逻辑
│   │   ├── backtest/       # 回测系统
│   │   │   ├── engine.py       # 回测引擎
│   │   │   ├── metrics.py      # 绩效指标
│   │   │   └── strategies/     # 策略库
│   │   ├── ml/             # 机器学习模块
│   │   │   ├── features.py     # 特征工程
│   │   │   └── models/         # 预测模型
│   │   ├── sentiment/      # 情感分析模块
│   │   │   └── sentiment_analyzer.py
│   │   ├── models/         # 数据模型
│   │   └── schemas/        # Pydantic模式
│   └── requirements.txt
│
└── frontend/                # React前端
    ├── src/
    │   ├── api/            # API调用
    │   ├── components/     # 组件
    │   │   └── charts/     # 图表组件
    │   ├── pages/          # 页面
    │   │   ├── Dashboard.tsx    # 仪表盘
    │   │   ├── StockDetail.tsx  # 股票详情
    │   │   ├── Screener.tsx     # 选股筛选
    │   │   ├── Portfolio.tsx    # 投资组合
    │   │   ├── Backtest.tsx     # 策略回测
    │   │   └── Prediction.tsx   # 智能预测
    │   ├── store/          # 状态管理
    │   └── types/          # 类型定义
    └── package.json
```

## API端点

### 股票数据
- `GET /api/v1/stocks/search?q={keyword}` - 搜索股票
- `GET /api/v1/stocks/{code}` - 股票信息
- `GET /api/v1/stocks/{code}/kline` - K线数据
- `GET /api/v1/stocks/{code}/quote` - 实时行情

### 技术指标
- `GET /api/v1/indicators/{code}/ma` - 移动平均线
- `GET /api/v1/indicators/{code}/macd` - MACD
- `GET /api/v1/indicators/{code}/rsi` - RSI
- `GET /api/v1/indicators/{code}/kdj` - KDJ
- `GET /api/v1/indicators/{code}/boll` - 布林带

### 选股筛选
- `POST /api/v1/screener/filter` - 多条件筛选
- `GET /api/v1/screener/presets` - 预设筛选条件

### 投资组合
- `GET /api/v1/portfolios/` - 获取所有组合
- `POST /api/v1/portfolios/` - 创建组合
- `GET /api/v1/portfolios/{id}/performance` - 组合绩效

### 策略回测
- `GET /api/v1/backtest/strategies` - 获取可用策略列表
- `POST /api/v1/backtest/run` - 运行回测
- `GET /api/v1/backtest/results/{id}` - 获取回测结果
- `GET /api/v1/backtest/history` - 回测历史记录

### 智能预测
- `GET /api/v1/ml/direction/{code}` - 价格方向预测
- `GET /api/v1/ml/price-range/{code}` - 价格区间预测
- `GET /api/v1/ml/price-target/{code}` - 价格目标位预测
- `GET /api/v1/ml/signal/{code}` - 交易信号
- `GET /api/v1/ml/comprehensive/{code}` - 综合预测
- `GET /api/v1/ml/sentiment/{code}` - 情感分析
- `GET /api/v1/ml/sentiment/market` - 市场情感
- `POST /api/v1/ml/batch-predict` - 批量预测

## 绩效指标说明

| 指标 | 说明 |
|------|------|
| 总收益 | 回测期间总收益率 |
| 年化收益 | 年化收益率 |
| 最大回撤 | 最大资金回撤幅度 |
| 夏普比率 | 风险调整后收益（越高越好，>1为良好） |
| 索提诺比率 | 仅考虑下行风险的夏普比率 |
| 卡尔玛比率 | 年化收益/最大回撤 |
| 胜率 | 盈利交易占比 |
| 盈亏比 | 总盈利/总亏损 |

## 开发说明

数据来源：AKShare（免费A股数据接口）

注意事项：
1. AKShare接口有请求频率限制，建议添加适当延时
2. 首次运行会自动创建SQLite数据库
3. 前端开发服务器会自动代理API请求到后端
4. 回测结果会保存到数据库，可查看历史记录
