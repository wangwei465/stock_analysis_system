#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智能预测系统自测脚本
====================================
用于验证智能预测系统的各项功能是否正常运行。

功能：
1. 读取现有持仓股票列表
2. 对每只股票执行完整的预测流程
3. 检测并报告潜在问题（NaN、异常值等）
4. 输出详细的测试报告

使用方法：
    cd backend
    python -m scripts.test_prediction

或者：
    python scripts/test_prediction.py
"""
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
import traceback

# 将 backend 目录添加到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import pandas as pd
import numpy as np

# =============================================================================
# 延迟导入项目模块（处理依赖问题）
# =============================================================================
IMPORTS_OK = True
IMPORT_ERRORS = []

# 核心模块导入
try:
    from app.core.data_fetcher import StockDataFetcher as DataFetcher
except ImportError as e:
    IMPORT_ERRORS.append(f"DataFetcher: {e}")
    DataFetcher = None

try:
    from app.ml.features import FeatureEngineer
except ImportError as e:
    IMPORT_ERRORS.append(f"FeatureEngineer: {e}")
    FeatureEngineer = None

try:
    from app.ml.models.signal_generator import SignalGenerator, ComprehensivePredictor
except ImportError as e:
    IMPORT_ERRORS.append(f"SignalGenerator: {e}")
    SignalGenerator = None
    ComprehensivePredictor = None

try:
    from app.sentiment.sentiment_analyzer import SentimentAnalysisService
except ImportError as e:
    IMPORT_ERRORS.append(f"SentimentAnalysisService: {e}")
    SentimentAnalysisService = None

# 检查核心模块
if DataFetcher is None or FeatureEngineer is None:
    IMPORTS_OK = False


# =============================================================================
# 测试配置
# =============================================================================
class TestConfig:
    """测试配置"""
    # 默认测试股票
    DEFAULT_TEST_STOCKS = [
        {'code': '000001', 'name': '平安银行'},
        {'code': '600519', 'name': '贵州茅台'},
        {'code': '000858', 'name': '五粮液'},
    ]

    # 预测周期
    FORWARD_DAYS = 5

    # 是否显示详细输出
    VERBOSE = True


# =============================================================================
# 测试结果类
# =============================================================================
class TestResult:
    """测试结果"""

    def __init__(self, stock_code: str, stock_name: str):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.success = False
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.prediction_result: Optional[Dict] = None
        self.sentiment_result: Optional[Dict] = None
        self.execution_time: float = 0

    def add_error(self, msg: str):
        """添加错误"""
        self.errors.append(msg)

    def add_warning(self, msg: str):
        """添加警告"""
        self.warnings.append(msg)


# =============================================================================
# 测试函数
# =============================================================================
def check_dataframe_issues(df: pd.DataFrame, name: str) -> List[str]:
    """
    检查 DataFrame 中的潜在问题

    Args:
        df: 要检查的 DataFrame
        name: 数据名称（用于报告）

    Returns:
        List[str]: 发现的问题列表
    """
    issues = []

    if df is None:
        issues.append(f"{name}: 数据为空")
        return issues

    if df.empty:
        issues.append(f"{name}: DataFrame 为空")
        return issues

    # 检查 NaN 值
    nan_count = df.isna().sum().sum()
    if nan_count > 0:
        nan_cols = df.columns[df.isna().any()].tolist()
        issues.append(f"{name}: 发现 {nan_count} 个 NaN 值，涉及列: {nan_cols[:5]}")

    # 检查无穷大值
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        inf_count = np.isinf(df[col]).sum()
        if inf_count > 0:
            issues.append(f"{name}: 列 '{col}' 包含 {inf_count} 个无穷大值")

    return issues


def test_single_stock(stock_code: str, stock_name: str, verbose: bool = True) -> TestResult:
    """
    测试单只股票的预测功能

    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        verbose: 是否输出详细信息

    Returns:
        TestResult: 测试结果
    """
    result = TestResult(stock_code, stock_name)
    start_time = datetime.now()

    if verbose:
        print(f"\n{'='*60}")
        print(f"测试股票: {stock_code} - {stock_name}")
        print('='*60)

    try:
        # =====================================================================
        # 步骤1: 获取历史数据
        # =====================================================================
        if verbose:
            print("[1/5] 获取历史数据...")

        # 计算日期范围（120个交易日）
        from datetime import timedelta
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")

        df = DataFetcher.get_daily_kline(stock_code, start_date=start_date, end_date=end_date)

        if df is None or df.empty:
            result.add_error("无法获取历史数据")
            return result

        # 确保 DataFrame 有正确的索引
        if 'date' in df.columns:
            df = df.set_index('date')

        if verbose:
            print(f"      获取到 {len(df)} 条记录")

        # =====================================================================
        # 步骤2: 生成特征
        # =====================================================================
        if verbose:
            print("[2/5] 生成特征...")

        features = FeatureEngineer.generate_all_features(df)

        # 检查特征数据
        feature_issues = check_dataframe_issues(features, "特征数据")
        for issue in feature_issues:
            result.add_warning(issue)

        if verbose:
            print(f"      生成 {len(features.columns)} 个特征")
            nan_after = features.isna().sum().sum()
            print(f"      NaN 值数量: {nan_after} (应为 0)")

        # =====================================================================
        # 步骤3: 综合预测
        # =====================================================================
        if verbose:
            print("[3/5] 执行综合预测...")

        if ComprehensivePredictor:
            prediction = ComprehensivePredictor.predict(df, TestConfig.FORWARD_DAYS, stock_code)
            result.prediction_result = prediction

            # 检查预测结果
            if prediction is None:
                result.add_error("预测结果为空")
            else:
                # 检查关键字段
                if 'direction' not in prediction:
                    result.add_warning("缺少方向预测")
                if 'signal' not in prediction:
                    result.add_warning("缺少信号预测")
                if 'price_range' not in prediction:
                    result.add_warning("缺少价格区间预测")

                if verbose:
                    print(f"      方向预测: {prediction.get('direction', {}).get('direction_label', 'N/A')}")
                    print(f"      交易信号: {prediction.get('signal', {}).get('signal_label', 'N/A')}")
                    print(f"      综合建议: {prediction.get('recommendation', {}).get('action', 'N/A')}")
        else:
            result.add_warning("ComprehensivePredictor 不可用")
            if verbose:
                print("      [跳过] ComprehensivePredictor 不可用")

        # =====================================================================
        # 步骤4: 情感分析
        # =====================================================================
        if verbose:
            print("[4/5] 执行情感分析...")

        if SentimentAnalysisService:
            try:
                sentiment_service = SentimentAnalysisService()
                sentiment = sentiment_service.get_sentiment_summary(stock_code)
                result.sentiment_result = sentiment

                if verbose:
                    combined = sentiment.get('combined', {})
                    print(f"      综合情绪: {combined.get('label', 'N/A')}")
                    print(f"      情绪得分: {combined.get('score', 0):.2f}")

            except Exception as e:
                result.add_warning(f"情感分析失败: {str(e)}")
                if verbose:
                    print(f"      情感分析失败: {e}")
        else:
            result.add_warning("SentimentAnalysisService 不可用")
            if verbose:
                print("      [跳过] SentimentAnalysisService 不可用")

        # =====================================================================
        # 步骤5: 信号生成器测试
        # =====================================================================
        if verbose:
            print("[5/5] 测试信号生成器...")

        if SignalGenerator:
            signal_gen = SignalGenerator(risk_tolerance='moderate', holding_period=5)
            signal = signal_gen.generate_signal(df, stock_code=stock_code)

            if signal:
                components = signal.get('components', {})
                if verbose:
                    print(f"      分析维度: {len(components)} 个")
                    for name, comp in components.items():
                        score = comp.get('score', 0) if isinstance(comp, dict) else 0
                        print(f"        - {name}: {score:+.2f}")
        else:
            result.add_warning("SignalGenerator 不可用")
            if verbose:
                print("      [跳过] SignalGenerator 不可用")

        # 标记成功
        result.success = len(result.errors) == 0

    except Exception as e:
        result.add_error(f"测试异常: {str(e)}")
        if verbose:
            traceback.print_exc()

    result.execution_time = (datetime.now() - start_time).total_seconds()

    if verbose:
        status = "[PASS] 通过" if result.success else "[FAIL] 失败"
        print(f"\n结果: {status} (耗时: {result.execution_time:.2f}s)")
        if result.errors:
            print(f"错误: {result.errors}")
        if result.warnings:
            print(f"警告: {result.warnings}")

    return result


def run_all_tests():
    """
    运行所有测试
    """
    print("\n" + "="*70)
    print("        智能预测系统自测脚本")
    print("        " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)

    # 显示导入状态
    if IMPORT_ERRORS:
        print("\n[警告] 部分模块导入失败:")
        for err in IMPORT_ERRORS:
            print(f"  - {err}")

    # 获取测试股票列表（直接使用默认列表，避免数据库依赖）
    positions = TestConfig.DEFAULT_TEST_STOCKS

    print(f"\n待测试股票: {len(positions)} 只")
    for p in positions:
        print(f"  - {p['code']} {p['name']}")

    # 执行测试
    results: List[TestResult] = []
    for pos in positions:
        result = test_single_stock(
            pos['code'],
            pos['name'],
            verbose=TestConfig.VERBOSE
        )
        results.append(result)

    # 汇总报告
    print("\n" + "="*70)
    print("                    测试报告汇总")
    print("="*70)

    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count
    warning_count = sum(len(r.warnings) for r in results)

    print(f"\n总计测试: {len(results)} 只股票")
    print(f"  [PASS] 通过: {success_count}")
    print(f"  [FAIL] 失败: {fail_count}")
    print(f"  [WARN] 警告: {warning_count}")

    # 详细失败报告
    if fail_count > 0:
        print("\n失败详情:")
        for r in results:
            if not r.success:
                print(f"\n  {r.stock_code} {r.stock_name}:")
                for err in r.errors:
                    print(f"    - {err}")

    # 警告报告
    if warning_count > 0:
        print("\n警告详情:")
        for r in results:
            if r.warnings:
                print(f"\n  {r.stock_code} {r.stock_name}:")
                for warn in r.warnings:
                    print(f"    - {warn}")

    print("\n" + "="*70)
    print("                    测试完成")
    print("="*70)

    return results


# =============================================================================
# 主函数
# =============================================================================
def main():
    """主函数"""
    if not IMPORTS_OK:
        print("\n[错误] 核心模块导入失败，无法运行测试")
        print("缺失模块:")
        for err in IMPORT_ERRORS:
            print(f"  - {err}")
        print("\n请确保已安装所有依赖: pip install -r requirements.txt")
        sys.exit(1)

    try:
        results = run_all_tests()

        # 返回退出码
        failed = any(not r.success for r in results)
        sys.exit(1 if failed else 0)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n测试执行出错: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
