# 后端安装文档

A股股票分析系统后端服务安装与配置指南。

## 环境要求

### 系统要求
- 操作系统：Windows 10/11、Linux、macOS
- 内存：建议 4GB 以上
- 磁盘空间：至少 2GB 可用空间

### 软件依赖
- Python 3.10 或更高版本
- pip 包管理器

### 验证 Python 版本
```bash
python --version
# 或
python3 --version
```

## 安装步骤

### 方式一：使用一键安装脚本（推荐）

在项目根目录执行：

```bash
# Windows
双击 install.bat

# 或命令行执行
install.bat
```

### 方式二：手动安装

#### 1. 创建虚拟环境

```bash
cd backend

# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

#### 2. 升级 pip

```bash
pip install --upgrade pip
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 验证安装

```bash
python -c "import fastapi; import akshare; print('依赖安装成功')"
```

## 依赖说明

| 分类 | 包名 | 版本要求 | 用途 |
|------|------|----------|------|
| Web框架 | fastapi | >=0.109.0 | 高性能异步Web框架 |
| Web框架 | uvicorn | >=0.27.0 | ASGI服务器 |
| Web框架 | python-multipart | >=0.0.6 | 文件上传支持 |
| 数据库 | sqlmodel | >=0.0.14 | ORM框架 |
| 数据库 | aiosqlite | >=0.19.0 | 异步SQLite驱动 |
| 数据源 | akshare | >=1.12.0 | A股数据接口 |
| 数据处理 | pandas | >=2.0.0 | 数据分析 |
| 数据处理 | numpy | >=1.24.0 | 数值计算 |
| 技术分析 | pandas-ta | >=0.3.14b | 技术指标计算 |
| 机器学习 | lightgbm | >=4.0.0 | 梯度提升模型 |
| 机器学习 | scikit-learn | >=1.3.0 | 机器学习工具 |
| 机器学习 | scipy | >=1.11.0 | 科学计算 |
| HTTP | httpx | >=0.26.0 | 异步HTTP客户端 |
| 工具 | python-dotenv | >=1.0.0 | 环境变量管理 |
| 工具 | cachetools | >=5.3.0 | 缓存工具 |
| 工具 | pydantic-settings | >=2.1.0 | 配置管理 |
| 测试 | pytest | >=7.4.0 | 测试框架 |
| 测试 | pytest-asyncio | >=0.23.0 | 异步测试支持 |

## 配置说明

### 默认配置

系统使用 `app/config.py` 管理配置，默认值如下：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| app_name | Stock Analysis System | 应用名称 |
| debug | True | 调试模式 |
| api_v1_prefix | /api/v1 | API路由前缀 |
| database_url | sqlite+aiosqlite:///./data/stock.db | 数据库连接 |
| cache_ttl | 300 | 缓存过期时间（秒） |

### 环境变量配置（可选）

创建 `.env` 文件覆盖默认配置：

```bash
# backend/.env

# 调试模式
DEBUG=false

# 数据库URL（支持其他数据库）
DATABASE_URL=sqlite+aiosqlite:///./data/stock.db

# 缓存过期时间（秒）
CACHE_TTL=600
```

## 启动服务

### 方式一：使用启动脚本

```bash
# Windows - 在项目根目录
双击 start-backend.bat

# 或命令行
start-backend.bat
```

### 方式二：手动启动

```bash
cd backend

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 启动参数说明

| 参数 | 说明 |
|------|------|
| --reload | 开发模式，代码变更自动重载 |
| --host 0.0.0.0 | 监听所有网络接口 |
| --port 8000 | 服务端口 |
| --workers 4 | 生产环境多进程（与--reload互斥） |

### 生产环境启动

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 验证安装

### 1. 健康检查

```bash
curl http://localhost:8000/health
# 或浏览器访问
```

预期响应：
```json
{"status": "healthy"}
```

### 2. API文档

访问 Swagger UI：
```
http://localhost:8000/docs
```

访问 ReDoc：
```
http://localhost:8000/redoc
```

### 3. 测试API

```bash
# 搜索股票
curl "http://localhost:8000/api/v1/stocks/search?q=平安"

# 获取K线数据
curl "http://localhost:8000/api/v1/stocks/000001/kline?period=daily&limit=30"
```

## 数据库

### 自动初始化

首次启动时自动创建：
- 数据目录：`backend/data/`
- 数据库文件：`backend/data/stock.db`

### 数据库表结构

| 表名 | 说明 |
|------|------|
| stocks | 股票基本信息 |
| daily_kline | 日K线数据 |
| weekly_kline | 周K线数据 |
| monthly_kline | 月K线数据 |
| stock_indicators | 技术指标缓存 |
| portfolios | 投资组合 |
| positions | 持仓记录 |
| transactions | 交易记录 |
| backtest_results | 回测结果 |

### 重置数据库

```bash
# 删除数据库文件
rm backend/data/stock.db

# 重启服务，自动重建
```

## 常见问题

### 1. pip 安装超时

使用国内镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. LightGBM 安装失败

Windows 用户可能需要安装 Visual C++ Build Tools：
- 下载地址：https://visualstudio.microsoft.com/visual-cpp-build-tools/

或使用预编译包：
```bash
pip install lightgbm --prefer-binary
```

### 3. AKShare 数据获取失败

- 检查网络连接
- AKShare 有请求频率限制，添加适当延时
- 部分数据在非交易时间可能不可用

### 4. 端口被占用

```bash
# Windows - 查找占用端口的进程
netstat -ano | findstr :8000

# 终止进程
taskkill /PID <进程ID> /F

# 或使用其他端口启动
uvicorn app.main:app --port 8001
```

### 5. 虚拟环境激活失败（Windows）

PowerShell 执行策略问题：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 6. 模块导入错误

确保在 backend 目录下启动：
```bash
cd backend
uvicorn app.main:app --reload
```

## 开发环境配置

### IDE 推荐配置

#### VS Code

安装扩展：
- Python
- Pylance
- Python Debugger

`.vscode/settings.json`：
```json
{
    "python.defaultInterpreterPath": "./backend/venv/Scripts/python.exe",
    "python.analysis.typeCheckingMode": "basic"
}
```

#### PyCharm

1. 设置项目解释器为 `backend/venv`
2. 标记 `backend` 为 Sources Root

### 运行测试

```bash
cd backend

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api.py -v

# 显示覆盖率
pytest --cov=app
```

## API 路由概览

| 路由前缀 | 说明 |
|----------|------|
| /api/v1/stocks | 股票数据 |
| /api/v1/indicators | 技术指标 |
| /api/v1/fundamental | 基本面分析 |
| /api/v1/screener | 选股筛选 |
| /api/v1/portfolios | 投资组合 |
| /api/v1/backtest | 策略回测 |
| /api/v1/ml | 机器学习预测 |
| /api/v1/ws | WebSocket实时推送 |

## 联系与支持

如遇问题，请检查：
1. Python 版本是否符合要求
2. 虚拟环境是否正确激活
3. 依赖是否完整安装
4. 网络连接是否正常
