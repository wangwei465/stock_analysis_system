"""Portfolio management API endpoints"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
import csv
import io

from app.database import get_session
from app.models.portfolio import Portfolio, Position, Transaction

router = APIRouter()


# Request/Response models
class PositionCreate(BaseModel):
    code: str
    name: str
    quantity: int
    avg_cost: float
    buy_date: Optional[date] = None
    notes: Optional[str] = None


class PositionUpdate(BaseModel):
    quantity: Optional[int] = None
    avg_cost: Optional[float] = None
    notes: Optional[str] = None


class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    initial_capital: Optional[float] = 1000000


class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    initial_capital: Optional[float] = None


class TransactionCreate(BaseModel):
    code: str
    trade_type: str  # BUY or SELL
    quantity: int
    price: float
    commission: Optional[float] = 0
    trade_date: Optional[date] = None


# Portfolio CRUD
@router.get("/")
async def list_portfolios(session: AsyncSession = Depends(get_session)):
    """Get all portfolios"""
    result = await session.execute(select(Portfolio))
    portfolios = result.scalars().all()
    return portfolios


@router.post("/")
async def create_portfolio(
    portfolio: PortfolioCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new portfolio"""
    db_portfolio = Portfolio(**portfolio.model_dump())
    session.add(db_portfolio)
    await session.commit()
    await session.refresh(db_portfolio)
    return db_portfolio


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get portfolio by ID"""
    portfolio = await session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Get positions
    result = await session.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    positions = result.scalars().all()

    return {
        "portfolio": portfolio,
        "positions": positions
    }


@router.put("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: int,
    update: PortfolioUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update portfolio"""
    portfolio = await session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(portfolio, key, value)

    await session.commit()
    await session.refresh(portfolio)
    return portfolio


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Delete portfolio"""
    portfolio = await session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    await session.delete(portfolio)
    await session.commit()
    return {"message": "Portfolio deleted"}


# Position CRUD
@router.post("/{portfolio_id}/positions")
async def add_position(
    portfolio_id: int,
    position: PositionCreate,
    session: AsyncSession = Depends(get_session)
):
    """Add position to portfolio"""
    portfolio = await session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    db_position = Position(
        portfolio_id=portfolio_id,
        **position.model_dump()
    )
    session.add(db_position)

    # Record transaction
    transaction = Transaction(
        portfolio_id=portfolio_id,
        code=position.code,
        trade_type="BUY",
        quantity=position.quantity,
        price=position.avg_cost,
        trade_date=position.buy_date or date.today()
    )
    session.add(transaction)

    await session.commit()
    await session.refresh(db_position)
    return db_position


@router.put("/{portfolio_id}/positions/{position_id}")
async def update_position(
    portfolio_id: int,
    position_id: int,
    update: PositionUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update position"""
    position = await session.get(Position, position_id)
    if not position or position.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail="Position not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(position, key, value)

    await session.commit()
    await session.refresh(position)
    return position


@router.delete("/{portfolio_id}/positions/{position_id}")
async def delete_position(
    portfolio_id: int,
    position_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Delete position (sell all)"""
    position = await session.get(Position, position_id)
    if not position or position.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail="Position not found")

    await session.delete(position)
    await session.commit()
    return {"message": "Position deleted"}


@router.get("/{portfolio_id}/transactions")
async def get_transactions(
    portfolio_id: int,
    limit: int = 50,
    session: AsyncSession = Depends(get_session)
):
    """Get transaction history"""
    result = await session.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.trade_date.desc())
        .limit(limit)
    )
    transactions = result.scalars().all()
    return transactions


@router.get("/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get portfolio performance metrics"""
    import asyncio
    from app.core.data_fetcher import StockDataFetcher

    portfolio = await session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Get positions
    result = await session.execute(
        select(Position).where(Position.portfolio_id == portfolio_id)
    )
    positions = result.scalars().all()

    if not positions:
        return {
            "portfolio_id": portfolio_id,
            "name": portfolio.name,
            "initial_capital": portfolio.initial_capital,
            "total_cost": 0,
            "total_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "cash": portfolio.initial_capital,
            "positions": []
        }

    # Parallel fetch all quotes (async, non-blocking)
    quote_tasks = [StockDataFetcher.get_realtime_quote_async(pos.code) for pos in positions]
    quotes = await asyncio.gather(*quote_tasks)

    # Build quote map
    quote_map = {}
    for pos, quote in zip(positions, quotes):
        quote_map[pos.code] = quote

    # Calculate performance
    total_cost = 0
    total_value = 0
    position_details = []

    for pos in positions:
        cost = pos.quantity * pos.avg_cost
        total_cost += cost

        # Get current price and pre_close from pre-fetched quotes
        quote = quote_map.get(pos.code)
        current_price = quote['price'] if quote else pos.avg_cost
        pre_close = quote['pre_close'] if quote else current_price
        value = pos.quantity * current_price
        total_value += value

        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0

        # Daily profit/loss
        daily_change = current_price - pre_close
        daily_pnl = daily_change * pos.quantity
        daily_pnl_pct = (daily_change / pre_close * 100) if pre_close > 0 else 0

        position_details.append({
            "id": pos.id,
            "code": pos.code,
            "name": pos.name,
            "quantity": pos.quantity,
            "avg_cost": pos.avg_cost,
            "current_price": current_price,
            "pre_close": pre_close,
            "cost": round(cost, 2),
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "daily_pnl": round(daily_pnl, 2),
            "daily_pnl_pct": round(daily_pnl_pct, 2),
            "weight": 0  # Will calculate below
        })

    # Calculate weights
    for detail in position_details:
        detail["weight"] = round(detail["value"] / total_value * 100, 2) if total_value > 0 else 0

    # Overall performance
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    return {
        "portfolio_id": portfolio_id,
        "name": portfolio.name,
        "initial_capital": portfolio.initial_capital,
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "cash": round(portfolio.initial_capital - total_cost, 2),
        "positions": position_details
    }


@router.get("/summary/all")
async def get_all_portfolios_summary(session: AsyncSession = Depends(get_session)):
    """Get summary of all portfolios combined"""
    import asyncio
    from app.core.data_fetcher import StockDataFetcher

    # Get all portfolios
    result = await session.execute(select(Portfolio))
    portfolios = result.scalars().all()

    if not portfolios:
        return {
            "portfolio_count": 0,
            "position_count": 0,
            "total_initial_capital": 0,
            "total_cost": 0,
            "total_value": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
            "daily_pnl": 0,
            "daily_pnl_pct": 0,
            "total_cash": 0,
            "position_ratio": 0,
            "portfolios": []
        }

    # Collect all positions from all portfolios
    all_positions = []
    portfolio_positions_map = {}  # portfolio_id -> [positions]

    for portfolio in portfolios:
        pos_result = await session.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )
        positions = pos_result.scalars().all()
        portfolio_positions_map[portfolio.id] = positions
        all_positions.extend(positions)

    # Collect unique stock codes and fetch all quotes in parallel
    unique_codes = list(set(pos.code for pos in all_positions))
    if unique_codes:
        quote_tasks = [StockDataFetcher.get_realtime_quote_async(code) for code in unique_codes]
        quotes = await asyncio.gather(*quote_tasks)
        quote_map = dict(zip(unique_codes, quotes))
    else:
        quote_map = {}

    # Calculate metrics
    total_initial_capital = 0
    total_cost = 0
    total_value = 0
    total_daily_pnl = 0
    position_count = len(all_positions)
    portfolio_summaries = []

    for portfolio in portfolios:
        total_initial_capital += portfolio.initial_capital
        positions = portfolio_positions_map.get(portfolio.id, [])

        portfolio_cost = 0
        portfolio_value = 0
        portfolio_daily_pnl = 0

        for pos in positions:
            cost = pos.quantity * pos.avg_cost
            portfolio_cost += cost
            total_cost += cost

            # Get current price from pre-fetched quotes
            quote = quote_map.get(pos.code)
            current_price = quote['price'] if quote else pos.avg_cost
            pre_close = quote['pre_close'] if quote else current_price

            value = pos.quantity * current_price
            portfolio_value += value
            total_value += value

            # Daily PnL
            daily_change = (current_price - pre_close) * pos.quantity
            portfolio_daily_pnl += daily_change
            total_daily_pnl += daily_change

        portfolio_pnl = portfolio_value - portfolio_cost
        portfolio_pnl_pct = (portfolio_pnl / portfolio_cost * 100) if portfolio_cost > 0 else 0
        portfolio_daily_pnl_pct = (portfolio_daily_pnl / (portfolio_value - portfolio_daily_pnl) * 100) if (portfolio_value - portfolio_daily_pnl) > 0 else 0

        portfolio_summaries.append({
            "id": portfolio.id,
            "name": portfolio.name,
            "total_value": round(portfolio_value, 2),
            "total_pnl": round(portfolio_pnl, 2),
            "total_pnl_pct": round(portfolio_pnl_pct, 2),
            "daily_pnl": round(portfolio_daily_pnl, 2),
            "daily_pnl_pct": round(portfolio_daily_pnl_pct, 2)
        })

    # Calculate overall metrics
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    daily_pnl_pct = (total_daily_pnl / (total_value - total_daily_pnl) * 100) if (total_value - total_daily_pnl) > 0 else 0
    total_cash = total_initial_capital - total_cost
    position_ratio = (total_cost / total_initial_capital * 100) if total_initial_capital > 0 else 0

    return {
        "portfolio_count": len(portfolios),
        "position_count": position_count,
        "total_initial_capital": round(total_initial_capital, 2),
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "daily_pnl": round(total_daily_pnl, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 2),
        "total_cash": round(total_cash, 2),
        "position_ratio": round(position_ratio, 2),
        "portfolios": portfolio_summaries
    }


# Transaction CRUD
@router.post("/{portfolio_id}/transactions")
async def create_transaction(
    portfolio_id: int,
    transaction: TransactionCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new transaction record"""
    portfolio = await session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if transaction.trade_type not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="trade_type must be BUY or SELL")

    db_transaction = Transaction(
        portfolio_id=portfolio_id,
        code=transaction.code,
        trade_type=transaction.trade_type,
        quantity=transaction.quantity,
        price=transaction.price,
        commission=transaction.commission or 0,
        trade_date=transaction.trade_date or date.today()
    )
    session.add(db_transaction)
    await session.commit()
    await session.refresh(db_transaction)
    return db_transaction


@router.delete("/{portfolio_id}/transactions/{transaction_id}")
async def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Delete a transaction record"""
    transaction = await session.get(Transaction, transaction_id)
    if not transaction or transaction.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await session.delete(transaction)
    await session.commit()
    return {"message": "Transaction deleted"}


@router.post("/{portfolio_id}/transactions/import")
async def import_transactions(
    portfolio_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Import transactions from CSV file.
    CSV format: code,trade_type,quantity,price,commission,trade_date
    Example: 000001,BUY,1000,10.50,5.25,2024-01-15
    """
    portfolio = await session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    try:
        decoded = content.decode('utf-8-sig')  # Handle BOM
    except UnicodeDecodeError:
        decoded = content.decode('gbk')  # Try GBK for Chinese Excel

    reader = csv.DictReader(io.StringIO(decoded))
    imported = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            code = row.get('code', '').strip()
            trade_type = row.get('trade_type', '').strip().upper()
            quantity = int(row.get('quantity', 0))
            price = float(row.get('price', 0))
            commission = float(row.get('commission', 0) or 0)
            trade_date_str = row.get('trade_date', '').strip()

            if not code or trade_type not in ['BUY', 'SELL'] or quantity <= 0 or price <= 0:
                errors.append(f"Row {row_num}: Invalid data")
                continue

            trade_date_val = date.fromisoformat(trade_date_str) if trade_date_str else date.today()

            db_transaction = Transaction(
                portfolio_id=portfolio_id,
                code=code,
                trade_type=trade_type,
                quantity=quantity,
                price=price,
                commission=commission,
                trade_date=trade_date_val
            )
            session.add(db_transaction)
            imported += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    await session.commit()
    return {
        "imported": imported,
        "errors": errors[:10],  # Return first 10 errors
        "total_errors": len(errors)
    }
