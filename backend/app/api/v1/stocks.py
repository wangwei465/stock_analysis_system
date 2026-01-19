"""Stock data API endpoints"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from app.core.data_fetcher import StockDataFetcher
from app.schemas.stock import (
    StockInfo, KlineData, KlineResponse,
    StockQuote, StockSearchResult,
    IntradayData, IntradayResponse
)

router = APIRouter()


@router.get("/search", response_model=List[StockSearchResult])
async def search_stocks(
    q: str = Query(..., min_length=1, description="Search keyword (code or name)"),
    limit: int = Query(20, ge=1, le=100, description="Max results")
):
    """Search stocks by code or name"""
    results = await StockDataFetcher.search_stocks_async(q, limit)
    return results


@router.get("/{code}", response_model=StockInfo)
async def get_stock_info(code: str):
    """Get stock basic information"""
    info = await StockDataFetcher.get_stock_info_async(code)
    if not info:
        raise HTTPException(status_code=404, detail=f"Stock {code} not found")
    return info


@router.get("/{code}/kline", response_model=KlineResponse)
async def get_kline(
    code: str,
    period: str = Query("day", pattern="^(day|week|month)$", description="K-line period"),
    start_date: Optional[str] = Query(None, pattern="^\\d{8}$", description="Start date (YYYYMMDD)"),
    end_date: Optional[str] = Query(None, pattern="^\\d{8}$", description="End date (YYYYMMDD)"),
    adjust: str = Query("qfq", pattern="^(qfq|hfq|none)$", description="Price adjustment")
):
    """
    Get K-line data for a stock

    Args:
        code: Stock code (e.g., 000001.SZ)
        period: K-line period (day/week/month)
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format
        adjust: Price adjustment type (qfq=forward, hfq=backward, none)
    """
    # Get stock info first
    stock_info = await StockDataFetcher.get_stock_info_async(code)
    if not stock_info:
        raise HTTPException(status_code=404, detail=f"Stock {code} not found")

    # Fetch K-line data based on period (async, non-blocking)
    if period == "day":
        df = await StockDataFetcher.get_daily_kline_async(code, start_date, end_date, adjust)
    elif period == "week":
        df = await StockDataFetcher.get_weekly_kline_async(code, start_date, end_date, adjust)
    else:  # month
        df = await StockDataFetcher.get_monthly_kline_async(code, start_date, end_date, adjust)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No K-line data found for {code}")

    # Convert to response format
    kline_data = []
    for _, row in df.iterrows():
        kline_data.append(KlineData(
            time=row['date'].strftime('%Y-%m-%d'),
            open=round(float(row['open']), 2),
            high=round(float(row['high']), 2),
            low=round(float(row['low']), 2),
            close=round(float(row['close']), 2),
            volume=int(row['volume']),
            amount=round(float(row['amount']), 2) if 'amount' in row and row['amount'] else None,
            turnover=round(float(row['turnover']), 2) if 'turnover' in row and row['turnover'] else None
        ))

    return KlineResponse(
        code=code,
        name=stock_info['name'],
        period=period,
        data=kline_data
    )


@router.get("/{code}/quote", response_model=StockQuote)
async def get_realtime_quote(code: str):
    """Get real-time stock quote"""
    quote = await StockDataFetcher.get_realtime_quote_async(code)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote not available for {code}")
    return quote


@router.get("/{code}/intraday", response_model=IntradayResponse)
async def get_intraday_data(code: str):
    """
    Get intraday minute data for timeline chart

    Args:
        code: Stock code (e.g., 000001.SZ)

    Returns:
        Intraday minute-level data with price and volume
    """
    import asyncio

    # Parallel fetch: stock info, quote, and intraday data
    stock_info_task = StockDataFetcher.get_stock_info_async(code)
    quote_task = StockDataFetcher.get_realtime_quote_async(code)
    intraday_task = StockDataFetcher.get_intraday_data_async(code)

    stock_info, quote, df = await asyncio.gather(
        stock_info_task, quote_task, intraday_task
    )

    if not stock_info:
        raise HTTPException(status_code=404, detail=f"Stock {code} not found")

    pre_close = quote['pre_close'] if quote else 0

    if df.empty:
        # Return empty data with pre_close
        return IntradayResponse(
            code=code,
            name=stock_info['name'],
            pre_close=pre_close,
            data=[]
        )

    # Calculate cumulative amount and average price
    intraday_data = []
    cumulative_amount = 0
    cumulative_volume = 0

    for _, row in df.iterrows():
        # AKShare 分钟线（stock_zh_a_minute）返回的 volume 字段口径通常为“手”（1 手 = 100 股）。
        # 为了和系统内部成交量/均价计算统一为“股”的口径，这里统一换算成股数。
        volume = int(row['volume']) * 100
        cumulative_volume += volume

        # Calculate amount: price * volume
        amount = float(row['close']) * volume
        cumulative_amount += amount

        # Calculate average price (均价)
        avg_price = cumulative_amount / cumulative_volume if cumulative_volume > 0 else float(row['close'])

        # Return full datetime for lightweight-charts compatibility
        # Format: "YYYY-MM-DD HH:MM" for proper time parsing
        time_str = row['time'].strftime('%Y-%m-%d %H:%M')

        intraday_data.append(IntradayData(
            time=time_str,
            price=round(float(row['close']), 2),
            avg_price=round(avg_price, 2),
            volume=volume,
            amount=round(amount, 2)
        ))

    return IntradayResponse(
        code=code,
        name=stock_info['name'],
        pre_close=pre_close,
        data=intraday_data
    )


@router.get("/", response_model=List[StockSearchResult])
async def get_stock_list(
    limit: int = Query(100, ge=1, le=1000, description="Max results")
):
    """Get list of all stocks"""
    df = await StockDataFetcher.get_stock_list_async()
    if df.empty:
        return []

    results = []
    for _, row in df.head(limit).iterrows():
        results.append(StockSearchResult(
            code=row['full_code'],
            name=row['name'],
            market=row['market']
        ))

    return results
