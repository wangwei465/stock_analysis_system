"""Technical indicators API endpoints"""
from typing import List, Optional, Literal
from fastapi import APIRouter, HTTPException, Query
from app.core.data_fetcher import StockDataFetcher
from app.core.indicator_calculator import IndicatorCalculator, format_indicator_for_chart
from app.schemas.stock import (
    MAData, MACDData, RSIData, KDJData, BOLLData, IndicatorData
)

router = APIRouter()


async def get_kline_data_async(
    code: str,
    kline_period: str = 'day',
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Helper to get kline data with validation (async, non-blocking)"""
    if kline_period == 'week':
        df = await StockDataFetcher.get_weekly_kline_async(code, start_date, end_date)
    elif kline_period == 'month':
        df = await StockDataFetcher.get_monthly_kline_async(code, start_date, end_date)
    else:
        df = await StockDataFetcher.get_daily_kline_async(code, start_date, end_date)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {code}")
    return df


@router.get("/{code}/ma", response_model=MAData)
async def get_ma(
    code: str,
    periods: str = Query("5,10,20,60", description="Comma-separated MA periods"),
    kline_period: str = Query("day", description="K-line period: day, week, month"),
    start_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYYMMDD)")
):
    """
    Get Moving Average indicators

    Args:
        code: Stock code
        periods: Comma-separated list of MA periods (e.g., "5,10,20,60")
        kline_period: K-line period (day, week, month)
    """
    df = await get_kline_data_async(code, kline_period, start_date, end_date)

    # Parse periods
    period_list = [int(p.strip()) for p in periods.split(',') if p.strip().isdigit()]
    if not period_list:
        period_list = [5, 10, 20, 60]

    # Calculate MAs
    ma_data = IndicatorCalculator.calculate_ma(df, period_list)

    # Format response
    result = {}
    for period in period_list:
        key = f'ma{period}'
        if key in ma_data.columns:
            result[key] = format_indicator_for_chart(df, ma_data[key])

    return MAData(**result)


@router.get("/{code}/macd", response_model=MACDData)
async def get_macd(
    code: str,
    fast: int = Query(12, ge=1, le=100, description="Fast EMA period"),
    slow: int = Query(26, ge=1, le=200, description="Slow EMA period"),
    signal: int = Query(9, ge=1, le=100, description="Signal line period"),
    kline_period: str = Query("day", description="K-line period: day, week, month"),
    start_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYYMMDD)")
):
    """Get MACD indicator"""
    df = await get_kline_data_async(code, kline_period, start_date, end_date)

    macd_data = IndicatorCalculator.calculate_macd(df, fast, slow, signal)

    return MACDData(
        macd=format_indicator_for_chart(df, macd_data['dif']),
        signal=format_indicator_for_chart(df, macd_data['dea']),
        histogram=format_indicator_for_chart(df, macd_data['macd'])
    )


@router.get("/{code}/rsi", response_model=RSIData)
async def get_rsi(
    code: str,
    period: int = Query(14, ge=1, le=100, description="RSI period"),
    kline_period: str = Query("day", description="K-line period: day, week, month"),
    start_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYYMMDD)")
):
    """Get RSI indicator"""
    df = await get_kline_data_async(code, kline_period, start_date, end_date)

    rsi_data = IndicatorCalculator.calculate_rsi(df, period)

    return RSIData(
        rsi=format_indicator_for_chart(df, rsi_data['rsi'])
    )


@router.get("/{code}/kdj", response_model=KDJData)
async def get_kdj(
    code: str,
    n: int = Query(9, ge=1, le=100, description="KDJ period"),
    m1: int = Query(3, ge=1, le=20, description="K smoothing"),
    m2: int = Query(3, ge=1, le=20, description="D smoothing"),
    kline_period: str = Query("day", description="K-line period: day, week, month"),
    start_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYYMMDD)")
):
    """Get KDJ indicator"""
    df = await get_kline_data_async(code, kline_period, start_date, end_date)

    kdj_data = IndicatorCalculator.calculate_kdj(df, n, m1, m2)

    return KDJData(
        k=format_indicator_for_chart(df, kdj_data['k']),
        d=format_indicator_for_chart(df, kdj_data['d']),
        j=format_indicator_for_chart(df, kdj_data['j'])
    )


@router.get("/{code}/boll", response_model=BOLLData)
async def get_boll(
    code: str,
    period: int = Query(20, ge=1, le=100, description="Bollinger period"),
    std: float = Query(2.0, ge=0.5, le=5.0, description="Standard deviation multiplier"),
    kline_period: str = Query("day", description="K-line period: day, week, month"),
    start_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYYMMDD)")
):
    """Get Bollinger Bands indicator"""
    df = await get_kline_data_async(code, kline_period, start_date, end_date)

    boll_data = IndicatorCalculator.calculate_boll(df, period, std)

    return BOLLData(
        upper=format_indicator_for_chart(df, boll_data['upper']),
        middle=format_indicator_for_chart(df, boll_data['mid']),
        lower=format_indicator_for_chart(df, boll_data['lower'])
    )


@router.get("/{code}/all")
async def get_all_indicators(
    code: str,
    ma_periods: str = Query("5,10,20,60", description="MA periods"),
    kline_period: str = Query("day", description="K-line period: day, week, month"),
    start_date: Optional[str] = Query(None, description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYYMMDD)")
):
    """Get all indicators at once"""
    df = await get_kline_data_async(code, kline_period, start_date, end_date)

    # Parse MA periods
    period_list = [int(p.strip()) for p in ma_periods.split(',') if p.strip().isdigit()]
    if not period_list:
        period_list = [5, 10, 20, 60]

    # Calculate all indicators
    all_indicators = IndicatorCalculator.calculate_all(df, period_list)

    # Format response
    result = {
        'ma': {},
        'macd': {},
        'rsi': [],
        'kdj': {},
        'boll': {}
    }

    # MA
    for col in all_indicators['ma'].columns:
        result['ma'][col] = format_indicator_for_chart(df, all_indicators['ma'][col])

    # MACD (dif->macd, dea->signal, macd->histogram)
    result['macd']['macd'] = format_indicator_for_chart(df, all_indicators['macd']['dif'])
    result['macd']['signal'] = format_indicator_for_chart(df, all_indicators['macd']['dea'])
    result['macd']['histogram'] = format_indicator_for_chart(df, all_indicators['macd']['macd'])

    # RSI
    result['rsi'] = format_indicator_for_chart(df, all_indicators['rsi']['rsi'])

    # KDJ
    for key in ['k', 'd', 'j']:
        result['kdj'][key] = format_indicator_for_chart(df, all_indicators['kdj'][key])

    # BOLL
    result['boll']['upper'] = format_indicator_for_chart(df, all_indicators['boll']['upper'])
    result['boll']['middle'] = format_indicator_for_chart(df, all_indicators['boll']['mid'])
    result['boll']['lower'] = format_indicator_for_chart(df, all_indicators['boll']['lower'])

    return result
