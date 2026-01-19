# AKShare 方法使用清单

本文档整理了本系统中所有 **AKShare** 的调用点与具体方法，用于快速定位数据来源、参数含义与返回字段的使用方式。

> 说明：系统后端采用“懒加载 + 缓存”策略使用 AKShare（避免启动慢、降低请求频率与失败概率）。  
> AKShare 版本要求：见 `backend/requirements.txt`（当前为 `akshare>=1.12.0`）。

## 1. 总览（本系统实际用到的方法）

| AKShare 方法 | 主要用途 | 代码位置（入口函数/模块） | 关键参数（本项目用法） |
|---|---|---|---|
| `ak.stock_info_a_code_name()` | 获取 A 股代码与名称列表 | `backend/app/core/data_fetcher.py` → `StockDataFetcher.get_stock_list()` | 无 |
| `ak.stock_zh_a_hist()` | 获取 A 股历史 K 线（日/周/月） | `backend/app/core/data_fetcher.py` → `get_daily_kline/get_weekly_kline/get_monthly_kline` | `symbol`、`period`、`start_date`、`end_date`、`adjust` |
| `ak.stock_bid_ask_em()` | 获取单只股票盘口/实时行情（item-value 结构） | `backend/app/core/data_fetcher.py` → `get_realtime_quote()`；`backend/app/core/fundamental_analyzer.py` → `_get_valuation_sync()` | `symbol` |
| `ak.stock_zh_a_minute()` | 获取分时分钟线（用于分时图/推送） | `backend/app/core/data_fetcher.py` → `get_intraday_data()` | `symbol`（Sina 格式）、`period='1'`、`adjust=''` |
| `ak.stock_zh_a_spot_em()` | 获取全市场 A 股实时快照（筛选用） | `backend/app/core/stock_screener.py` → `_fetch_all_stocks_sync()` | 无 |
| `ak.stock_individual_info_em()` | 获取个股基本信息（item-value 结构） | `backend/app/core/fundamental_analyzer.py` → `_get_company_profile_sync()`；`_get_valuation_sync()` | `symbol` |
| `ak.stock_financial_report_sina()` | 获取财报（利润表/资产负债表/现金流量表） | `backend/app/core/fundamental_analyzer.py` → `_get_financial_report_sync()` | `stock`、`symbol`（报表类型中文名） |
| `ak.stock_history_dividend_detail()` | 获取历史分红等信息 | `backend/app/core/fundamental_analyzer.py` → `_get_dividend_history_sync()` | `symbol`、`indicator='分红'` |
| `ak.stock_circulate_stock_holder()` | 获取流通股东数据 | `backend/app/core/fundamental_analyzer.py` → `_get_top_holders_sync()` | `symbol` |
| `ak.stock_news_em()` | 获取个股相关新闻列表 | `backend/app/sentiment/sentiment_analyzer.py` → `StockNewsFetcher.get_stock_news()` | `symbol`（纯数字代码） |
| `ak.stock_info_global_cls()` | 获取市场资讯（财联社电报） | `backend/app/sentiment/sentiment_analyzer.py` → `StockNewsFetcher.get_market_news()` | `symbol='全部'` |

## 2. 逐个方法说明（结合本项目的字段与处理逻辑）

### 2.1 `ak.stock_info_a_code_name()`

- **用途**：获取 A 股全量股票列表（代码、名称等基础字段）。
- **本项目处理**：
  - 追加 `market` 字段：代码以 `6` 开头视为 `SH`，否则视为 `SZ`。
  - 追加 `full_code`：形如 `000001.SZ` / `600000.SH`，便于前后端统一传参。
- **代码位置**：`backend/app/core/data_fetcher.py` → `StockDataFetcher.get_stock_list()`。

### 2.2 `ak.stock_zh_a_hist(symbol, period, start_date, end_date, adjust)`

- **用途**：获取历史 K 线数据。
- **本项目用法**：
  - `period`：`daily` / `weekly` / `monthly`（分别对应日线/周线/月线）。
  - `adjust`：使用 `qfq`（前复权）作为默认；当调用方传入 `none` 时转换为空串 `''`（表示不复权）。
  - `start_date/end_date`：格式为 `YYYYMMDD`。
- **字段处理（兼容性）**：
  - AKShare 不同版本的返回列名可能存在差异，本项目做了**动态列名映射**（如 `日期/开盘/收盘/最高/最低/成交量...` → `date/open/close/high/low/volume...`）。
  - 将 `date` 转换为 `datetime`，便于后续绘图/计算。
- **代码位置**：`backend/app/core/data_fetcher.py` → `get_daily_kline/get_weekly_kline/get_monthly_kline`。

### 2.3 `ak.stock_bid_ask_em(symbol)`

- **用途**：获取单只股票盘口/实时行情，返回结构通常为两列：`item`（指标名）与 `value`（指标值）。
- **本项目处理**：
  - 将 `item/value` 转为字典，取出 `名称/最新/涨跌/涨幅/今开/最高/最低/昨收/总手/金额` 等字段。
  - 特别注意：`总手` 的单位是“手”（1 手 = 100 股）；`金额` 通常为“元”。
- **代码位置**：
  - `backend/app/core/data_fetcher.py` → `StockDataFetcher.get_realtime_quote()`（按需获取单只股票，避免全量快照接口）。
  - `backend/app/core/fundamental_analyzer.py` → `_get_valuation_sync()`（结合个股信息补全估值字段）。

### 2.4 `ak.stock_zh_a_minute(symbol, period='1', adjust='')`

- **用途**：获取分钟级别分时数据（本项目用于分时图与 websocket 推送）。
- **本项目用法**：
  - `symbol`：使用 Sina 格式（`sh600000` / `sz000001`）。
  - `period='1'`：1 分钟级别；`adjust=''`：不复权。
- **字段与单位注意**：
  - 接口返回列中时间字段常见为 `day`（本项目重命名为 `time`）。
  - `volume` 通常为“手”，前端展示或金额计算时需要按 `*100` 转为“股”。
- **代码位置**：
  - 获取分时序列：`backend/app/core/data_fetcher.py` → `StockDataFetcher.get_intraday_data()`。
  - 分时累计均价/成交量换算：`backend/app/api/v1/stocks.py`、`backend/app/api/v1/websocket.py`。

### 2.5 `ak.stock_zh_a_spot_em()`

- **用途**：获取全市场 A 股实时快照（全量列表）。
- **本项目处理**：
  - 用于条件筛选（Stock Screener）。
  - 将 `总市值/流通市值` 从“元”转换为“亿元”（除以 `100000000`），便于前端展示与筛选阈值统一。
- **代码位置**：`backend/app/core/stock_screener.py` → `_fetch_all_stocks_sync()`。

### 2.6 `ak.stock_individual_info_em(symbol)`

- **用途**：获取个股基本信息（通常也是 `item/value` 结构）。
- **本项目处理**：
  - 公司概况：提取 `股票简称/行业/总市值/流通市值/总股本/流通股/市盈率-动态/市净率/上市时间` 等字段。
  - 估值补全：在 `_get_valuation_sync()` 中作为补充数据源，用于补齐 PE/PB/市值等。
- **代码位置**：`backend/app/core/fundamental_analyzer.py` → `_get_company_profile_sync()`、`_get_valuation_sync()`。

### 2.7 `ak.stock_financial_report_sina(stock, symbol)`

- **用途**：获取财报表格数据（利润表/资产负债表/现金流量表）。
- **本项目用法**：
  - `stock`：股票代码（纯数字）。
  - `symbol`：报表类型中文名（通过 `report_type` → 中文名映射实现）。
  - 取最近 `limit` 期数据（`head(limit)`）。
- **代码位置**：`backend/app/core/fundamental_analyzer.py` → `_get_financial_report_sync()`、`get_financial_data()`。

### 2.8 `ak.stock_history_dividend_detail(symbol, indicator='分红')`

- **用途**：获取历史分红等权益信息。
- **本项目用法**：固定 `indicator='分红'`，并在 API 层做 `limit` 截断。
- **代码位置**：`backend/app/core/fundamental_analyzer.py` → `_get_dividend_history_sync()`、`get_dividend_history()`。

### 2.9 `ak.stock_circulate_stock_holder(symbol)`

- **用途**：获取流通股东数据。
- **本项目处理**：
  - 取最新一期（`季度` 最大值）作为展示口径。
  - 输出字段：`股东名称/股东性质/持股数量/占流通股比例/增减` 等。
- **代码位置**：`backend/app/core/fundamental_analyzer.py` → `_get_top_holders_sync()`、`get_top_holders()`。

### 2.10 `ak.stock_news_em(symbol)`

- **用途**：获取个股相关新闻。
- **本项目用法**：
  - `symbol`：需要传**纯数字代码**；因此会对入参做清洗（去掉 `sh/sz` 前缀与 `.`）。
  - 取前 `limit` 条，用于情绪分析。
- **代码位置**：`backend/app/sentiment/sentiment_analyzer.py` → `StockNewsFetcher.get_stock_news()`。

### 2.11 `ak.stock_info_global_cls(symbol='全部')`

- **用途**：获取市场资讯（财联社电报）。
- **本项目用法**：
  - `symbol='全部'` 获取全量资讯，再取前 `limit` 条。
  - 考虑到列名在不同环境可能存在差异，本项目按列索引位置取 `title/content/date/time`。
- **代码位置**：`backend/app/sentiment/sentiment_analyzer.py` → `StockNewsFetcher.get_market_news()`。

## 3. 使用注意事项（建议）

- **频率限制/稳定性**：AKShare 接口对访问频率较敏感，建议配合缓存（本项目已对股票列表/筛选数据做了 TTL 缓存）。
- **列名兼容**：部分接口返回列名在不同版本可能变化，建议像本项目一样做列名映射或按索引读取。
- **单位口径**：
  - `stock_zh_a_minute`：`volume` 多为“手”，需要按 `*100` 转换为“股”。
  - 市值字段：建议统一到“亿元”或“元”，避免前后端阈值不一致。

