"""Fundamental data API endpoints"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.core.fundamental_analyzer import FundamentalAnalyzer

router = APIRouter()


@router.get("/{code}/profile")
async def get_company_profile(code: str):
    """Get company profile and basic information"""
    profile = await FundamentalAnalyzer.get_company_profile(code)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile not found for {code}")
    return profile


@router.get("/{code}/financial")
async def get_financial_data(
    code: str,
    report_type: str = Query("income", pattern="^(income|balance|cashflow)$"),
    limit: int = Query(8, ge=1, le=20)
):
    """
    Get financial statement data

    Args:
        code: Stock code
        report_type: income (利润表), balance (资产负债表), cashflow (现金流量表)
        limit: Number of reports to return
    """
    data = await FundamentalAnalyzer.get_financial_data(code, report_type, limit)
    if not data:
        raise HTTPException(status_code=404, detail=f"Financial data not found for {code}")
    return data


@router.get("/{code}/valuation")
async def get_valuation(code: str):
    """Get valuation metrics (PE, PB, PS, etc.)"""
    valuation = await FundamentalAnalyzer.get_valuation(code)
    if not valuation:
        raise HTTPException(status_code=404, detail=f"Valuation not found for {code}")
    return valuation


@router.get("/{code}/dividend")
async def get_dividend_history(code: str, limit: int = Query(10, ge=1, le=50)):
    """Get dividend history"""
    dividends = await FundamentalAnalyzer.get_dividend_history(code, limit)
    return dividends or []


@router.get("/{code}/holders")
async def get_top_holders(code: str):
    """Get top 10 shareholders"""
    holders = await FundamentalAnalyzer.get_top_holders(code)
    return holders or []
