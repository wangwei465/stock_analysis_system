"""
ML预测API路由
"""
import asyncio
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.data_fetcher import StockDataFetcher
from app.core.async_utils import run_sync
from app.ml.models.price_direction import QuickPredictionModel
from app.ml.models.price_range import QuickPriceRangePredictor, PriceTargetPredictor
from app.ml.models.signal_generator import SignalGenerator, ComprehensivePredictor
from app.sentiment.sentiment_analyzer import SentimentAnalysisService

router = APIRouter()


class PredictionRequest(BaseModel):
    """预测请求"""
    stock_code: str = Field(..., description="股票代码")
    forward_days: int = Field(default=5, ge=1, le=30, description="预测天数")
    risk_tolerance: str = Field(default="moderate", description="风险偏好: conservative/moderate/aggressive")


class PredictionResponse(BaseModel):
    """预测响应"""
    stock_code: str
    stock_name: Optional[str]
    current_price: float
    prediction_date: str
    forward_days: int
    direction: dict
    price_range: dict
    signal: dict
    sentiment: Optional[dict]
    risk: dict
    recommendation: dict


@router.get("/direction/{code}")
async def predict_direction(
    code: str,
    days: int = Query(default=5, ge=1, le=30, description="预测天数")
):
    """
    预测价格方向

    基于技术指标的快速方向预测
    """
    try:
        # 获取历史数据 (async, non-blocking)
        df = await StockDataFetcher.get_daily_kline_async(code)

        if df is None or len(df) < 60:
            raise HTTPException(status_code=400, detail="数据不足，需要至少60天历史数据")

        # 预测 (CPU-bound, run in thread pool)
        result = await run_sync(QuickPredictionModel.predict, df)

        return {
            "stock_code": code,
            "forward_days": days,
            "prediction": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-range/{code}")
async def predict_price_range(
    code: str,
    days: int = Query(default=5, ge=1, le=30, description="预测天数")
):
    """
    预测价格区间

    基于历史波动率预测未来价格区间
    """
    try:
        df = await StockDataFetcher.get_daily_kline_async(code)

        if df is None or len(df) < 60:
            raise HTTPException(status_code=400, detail="数据不足")

        result = await run_sync(QuickPriceRangePredictor.predict, df, days)

        return {
            "stock_code": code,
            "prediction": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/price-target/{code}")
async def predict_price_target(
    code: str,
    days: int = Query(default=20, ge=5, le=60, description="目标周期")
):
    """
    预测价格目标位

    结合技术分析预测目标价位
    """
    try:
        df = await StockDataFetcher.get_daily_kline_async(code)

        if df is None or len(df) < 120:
            raise HTTPException(status_code=400, detail="数据不足，需要至少120天历史数据")

        result = await run_sync(PriceTargetPredictor.predict, df, days)

        return {
            "stock_code": code,
            "prediction": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signal/{code}")
async def get_trading_signal(
    code: str,
    risk_tolerance: str = Query(default="moderate", pattern="^(conservative|moderate|aggressive)$"),
    holding_period: int = Query(default=5, ge=1, le=30)
):
    """
    获取交易信号

    综合多种指标生成买卖信号
    """
    try:
        # Parallel fetch: kline and stock info
        df_task = StockDataFetcher.get_daily_kline_async(code)
        info_task = StockDataFetcher.get_stock_info_async(code)

        df, stock_info = await asyncio.gather(df_task, info_task)

        if df is None or len(df) < 60:
            raise HTTPException(status_code=400, detail="数据不足")

        generator = SignalGenerator(
            risk_tolerance=risk_tolerance,
            holding_period=holding_period
        )

        result = await run_sync(generator.generate_signal, df)

        stock_name = stock_info.get('name', code) if stock_info else code

        return {
            "stock_code": code,
            "stock_name": stock_name,
            "signal": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comprehensive/{code}")
async def get_comprehensive_prediction(
    code: str,
    forward_days: int = Query(default=5, ge=1, le=30),
    include_sentiment: bool = Query(default=True, description="是否包含情感分析")
):
    """
    综合预测

    整合方向预测、价格区间、交易信号、情感分析
    """
    try:
        # Parallel fetch: kline and stock info
        df_task = StockDataFetcher.get_daily_kline_async(code)
        info_task = StockDataFetcher.get_stock_info_async(code)

        df, stock_info = await asyncio.gather(df_task, info_task)

        if df is None or len(df) < 60:
            raise HTTPException(status_code=400, detail="数据不足")

        # 综合预测 (CPU-bound)
        result = await run_sync(ComprehensivePredictor.predict, df, forward_days)

        stock_name = stock_info.get('name', code) if stock_info else code

        result['stock_code'] = code
        result['stock_name'] = stock_name
        result['forward_days'] = forward_days
        result['prediction_date'] = datetime.now().strftime('%Y-%m-%d')

        # 情感分析 (run in thread pool to avoid blocking)
        if include_sentiment:
            try:
                def get_sentiment():
                    service = SentimentAnalysisService()
                    return service.get_sentiment_summary(code)

                sentiment = await run_sync(get_sentiment)
                result['sentiment'] = sentiment
            except Exception as e:
                result['sentiment'] = {
                    'status': 'error',
                    'message': str(e)
                }

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/{code}")
async def get_sentiment_analysis(
    code: str,
    limit: int = Query(default=20, ge=5, le=50, description="新闻数量")
):
    """
    获取情感分析

    分析股票相关新闻的情感倾向
    """
    try:
        def analyze():
            service = SentimentAnalysisService()
            return service.get_sentiment_summary(code)

        result = await run_sync(analyze)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/market")
async def get_market_sentiment(
    limit: int = Query(default=30, ge=10, le=50)
):
    """
    获取市场情感

    分析整体市场情绪
    """
    try:
        def analyze():
            service = SentimentAnalysisService()
            return service.analyze_market_sentiment(limit)

        result = await run_sync(analyze)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-predict")
async def batch_predict(
    stock_codes: list[str],
    forward_days: int = Query(default=5, ge=1, le=30)
):
    """
    批量预测

    同时预测多只股票 (并行处理)
    """
    if len(stock_codes) > 10:
        raise HTTPException(status_code=400, detail="一次最多预测10只股票")

    async def predict_single(code: str):
        """Predict for a single stock"""
        try:
            # Parallel fetch kline and stock info
            df_task = StockDataFetcher.get_daily_kline_async(code)
            info_task = StockDataFetcher.get_stock_info_async(code)

            df, stock_info = await asyncio.gather(df_task, info_task)

            if df is not None and len(df) >= 60:
                # Run predictions in thread pool
                def do_predictions():
                    direction = QuickPredictionModel.predict(df)
                    generator = SignalGenerator()
                    signal = generator.generate_signal(df)
                    return direction, signal

                direction, signal = await run_sync(do_predictions)

                return {
                    'stock_code': code,
                    'stock_name': stock_info.get('name', code) if stock_info else code,
                    'current_price': float(df['close'].iloc[-1]),
                    'direction': direction.get('direction_label'),
                    'direction_confidence': direction.get('confidence'),
                    'signal': signal.get('signal_label'),
                    'signal_confidence': signal.get('confidence'),
                    'status': 'success'
                }
            else:
                return {
                    'stock_code': code,
                    'status': 'error',
                    'message': '数据不足'
                }

        except Exception as e:
            return {
                'stock_code': code,
                'status': 'error',
                'message': str(e)
            }

    # Run all predictions in parallel
    results = await asyncio.gather(*[predict_single(code) for code in stock_codes])

    return {
        "forward_days": forward_days,
        "results": list(results),
        "success_count": sum(1 for r in results if r.get('status') == 'success'),
        "error_count": sum(1 for r in results if r.get('status') == 'error')
    }
