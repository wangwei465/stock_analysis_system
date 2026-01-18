"""Backtest API endpoints"""
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel

from app.database import get_session
from app.models.backtest import BacktestResult
from app.backtest.engine import run_backtest, get_available_strategies

router = APIRouter()


class BacktestRequest(BaseModel):
    """Backtest request body"""
    strategy: str
    stock_code: str
    params: Optional[Dict[str, Any]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 1000000
    commission: float = 0.0003
    slippage: float = 0.001


@router.get("/strategies")
async def list_strategies():
    """Get available strategies"""
    return get_available_strategies()


@router.post("/run")
async def run_backtest_api(
    request: BacktestRequest,
    save: bool = Query(True, description="Save result to database"),
    session: AsyncSession = Depends(get_session)
):
    """
    Run backtest for a single stock

    Args:
        request: Backtest configuration
        save: Whether to save result to database
    """
    try:
        result = await run_backtest(
            strategy_name=request.strategy,
            stock_code=request.stock_code,
            params=request.params,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            commission=request.commission,
            slippage=request.slippage
        )

        # Save to database if requested
        if save:
            metrics = result["metrics"]
            db_result = BacktestResult(
                strategy_name=request.strategy,
                strategy_display_name=result["strategy"]["name"],
                params=json.dumps(request.params or {}),
                stock_code=request.stock_code,
                stock_name=result["stock"]["name"],
                start_date=result["period"]["start"],
                end_date=result["period"]["end"],
                initial_capital=request.initial_capital,
                final_capital=metrics["final_capital"],
                total_return=metrics["total_return"],
                annualized_return=metrics["annualized_return"],
                max_drawdown=metrics["max_drawdown"],
                sharpe_ratio=metrics["sharpe_ratio"],
                win_rate=metrics["win_rate"],
                trade_count=metrics["trade_count"],
                result_detail=json.dumps(result)
            )
            session.add(db_result)
            await session.commit()
            await session.refresh(db_result)

            result["id"] = db_result.id

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/results/{result_id}")
async def get_backtest_result(
    result_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get backtest result by ID"""
    result = await session.get(BacktestResult, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    # Parse full result
    return json.loads(result.result_detail)


@router.get("/history")
async def get_backtest_history(
    limit: int = Query(20, ge=1, le=100),
    strategy: Optional[str] = None,
    stock_code: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """Get backtest history"""
    query = select(BacktestResult).order_by(BacktestResult.created_at.desc())

    if strategy:
        query = query.where(BacktestResult.strategy_name == strategy)
    if stock_code:
        query = query.where(BacktestResult.stock_code == stock_code)

    query = query.limit(limit)
    result = await session.execute(query)
    results = result.scalars().all()

    return [
        {
            "id": r.id,
            "strategy_name": r.strategy_display_name,
            "stock_code": r.stock_code,
            "stock_name": r.stock_name,
            "period": f"{r.start_date} ~ {r.end_date}",
            "total_return": r.total_return,
            "annualized_return": r.annualized_return,
            "max_drawdown": r.max_drawdown,
            "sharpe_ratio": r.sharpe_ratio,
            "win_rate": r.win_rate,
            "trade_count": r.trade_count,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for r in results
    ]


@router.delete("/results/{result_id}")
async def delete_backtest_result(
    result_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Delete backtest result"""
    result = await session.get(BacktestResult, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    await session.delete(result)
    await session.commit()
    return {"message": "Result deleted"}
