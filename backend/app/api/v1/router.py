"""API v1 Router - aggregates all endpoints"""
from fastapi import APIRouter
from .stocks import router as stocks_router
from .indicators import router as indicators_router
from .fundamental import router as fundamental_router
from .screener import router as screener_router
from .portfolio import router as portfolio_router
from .websocket import router as websocket_router
from .backtest import router as backtest_router
from .ml import router as ml_router
from .cache import router as cache_router
from .prediction_records import router as prediction_records_router
from .equity_bond_spread import router as equity_bond_spread_router

api_router = APIRouter()

api_router.include_router(stocks_router, prefix="/stocks", tags=["stocks"])
api_router.include_router(indicators_router, prefix="/indicators", tags=["indicators"])
api_router.include_router(fundamental_router, prefix="/fundamental", tags=["fundamental"])
api_router.include_router(screener_router, prefix="/screener", tags=["screener"])
api_router.include_router(portfolio_router, prefix="/portfolios", tags=["portfolios"])
api_router.include_router(websocket_router, prefix="/ws", tags=["websocket"])
api_router.include_router(backtest_router, prefix="/backtest", tags=["backtest"])
api_router.include_router(ml_router, prefix="/ml", tags=["ml"])
api_router.include_router(cache_router, prefix="/cache", tags=["cache"])
api_router.include_router(prediction_records_router, prefix="/prediction-records", tags=["prediction-records"])
api_router.include_router(equity_bond_spread_router, prefix="/equity-bond-spread", tags=["equity-bond-spread"])
