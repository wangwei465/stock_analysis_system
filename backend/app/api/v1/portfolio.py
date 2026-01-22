"""Portfolio management API endpoints"""
from typing import Dict, List, Optional
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

async def _get_positions_by_code(
    session: AsyncSession,
    portfolio_id: int,
    code: str,
) -> List[Position]:
    result = await session.execute(
        select(Position)
        .where(Position.portfolio_id == portfolio_id, Position.code == code)
        .order_by(Position.id)
    )
    return result.scalars().all()


async def _consolidate_positions_by_code(
    session: AsyncSession,
    portfolio_id: int,
    code: str,
) -> Optional[Position]:
    """
    Ensure at most one Position row exists for (portfolio_id, code).
    If multiple rows exist, merge them into the earliest row and delete the rest.
    """
    positions = await _get_positions_by_code(session, portfolio_id, code)
    if not positions:
        return None
    if len(positions) == 1:
        return positions[0]

    primary = positions[0]
    total_qty = sum(p.quantity for p in positions)
    total_cost = sum(p.quantity * p.avg_cost for p in positions)
    primary.quantity = total_qty
    primary.avg_cost = (total_cost / total_qty) if total_qty > 0 else primary.avg_cost

    # Best-effort preserve metadata
    for p in positions:
        if p.name and not primary.name:
            primary.name = p.name
        if p.buy_date and (primary.buy_date is None or p.buy_date < primary.buy_date):
            primary.buy_date = p.buy_date

    for extra in positions[1:]:
        await session.delete(extra)

    return primary


async def _apply_trade_to_position(
    session: AsyncSession,
    portfolio_id: int,
    code: str,
    trade_type: str,
    quantity: int,
    price: float,
    commission: float,
    trade_date: date,
    name: Optional[str] = None,
) -> None:
    """
    Apply a BUY/SELL transaction to positions table so that holdings and
    transaction records stay in sync.
    """
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be > 0")
    if price <= 0:
        raise HTTPException(status_code=400, detail="price must be > 0")
    if commission < 0:
        raise HTTPException(status_code=400, detail="commission must be >= 0")

    position = await _consolidate_positions_by_code(session, portfolio_id, code)

    if trade_type == "BUY":
        safe_name = (name or "").strip()
        if position:
            total_cost = position.quantity * position.avg_cost + quantity * price + commission
            total_qty = position.quantity + quantity
            position.quantity = total_qty
            position.avg_cost = total_cost / total_qty
            if safe_name:
                position.name = safe_name
            if position.buy_date is None or trade_date < position.buy_date:
                position.buy_date = trade_date
        else:
            if not safe_name:
                safe_name = code
            avg_cost = (quantity * price + commission) / quantity
            session.add(
                Position(
                    portfolio_id=portfolio_id,
                    code=code,
                    name=safe_name,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    buy_date=trade_date,
                )
            )
        return

    if trade_type == "SELL":
        if not position:
            raise HTTPException(status_code=400, detail="Position not found for SELL")
        if quantity > position.quantity:
            raise HTTPException(status_code=400, detail="Sell quantity exceeds position quantity")

        position.quantity -= quantity
        if position.quantity == 0:
            await session.delete(position)
        return

    raise HTTPException(status_code=400, detail="trade_type must be BUY or SELL")


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
    name: Optional[str] = None
    trade_type: str  # BUY, SELL, DIVIDEND, TAX
    quantity: Optional[int] = None  # Required for BUY/SELL, not for DIVIDEND/TAX
    price: float  # Trade price for BUY/SELL, amount for DIVIDEND/TAX
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
    total_dividend = 0
    total_tax = 0
    position_details = []

    for pos in positions:
        cost = pos.quantity * pos.avg_cost
        total_cost += cost
        total_dividend += pos.total_dividend
        total_tax += pos.total_tax

        # Get current price and pre_close from pre-fetched quotes
        quote = quote_map.get(pos.code)
        current_price = quote['price'] if quote else pos.avg_cost
        pre_close = quote['pre_close'] if quote else current_price
        value = pos.quantity * current_price
        total_value += value

        # PnL = market value - cost (NOT including dividend/tax)
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
            "total_dividend": round(pos.total_dividend, 2),
            "total_tax": round(pos.total_tax, 2),
            "weight": 0  # Will calculate below
        })

    # Calculate weights
    for detail in position_details:
        detail["weight"] = round(detail["value"] / total_value * 100, 2) if total_value > 0 else 0

    # Overall performance (pnl NOT including dividend/tax, shown separately)
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
        "total_dividend": round(total_dividend, 2),
        "total_tax": round(total_tax, 2),
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

    valid_types = ["BUY", "SELL", "DIVIDEND", "TAX"]
    if transaction.trade_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"trade_type must be one of {valid_types}")

    trade_date_val = transaction.trade_date or date.today()
    commission_val = transaction.commission or 0

    # Handle BUY/SELL - update position quantity and cost
    if transaction.trade_type in ["BUY", "SELL"]:
        if not transaction.quantity or transaction.quantity <= 0:
            raise HTTPException(status_code=400, detail="quantity is required for BUY/SELL")
        await _apply_trade_to_position(
            session=session,
            portfolio_id=portfolio_id,
            code=transaction.code,
            trade_type=transaction.trade_type,
            quantity=transaction.quantity,
            price=transaction.price,
            commission=commission_val,
            trade_date=trade_date_val,
            name=transaction.name,
        )

    # Handle DIVIDEND/TAX - update position dividend/tax totals
    elif transaction.trade_type in ["DIVIDEND", "TAX"]:
        if transaction.price <= 0:
            raise HTTPException(status_code=400, detail="amount must be > 0")
        position = await _consolidate_positions_by_code(session, portfolio_id, transaction.code)
        if not position:
            raise HTTPException(status_code=400, detail="Position not found for DIVIDEND/TAX")
        if transaction.trade_type == "DIVIDEND":
            position.total_dividend += transaction.price
        else:  # TAX
            position.total_tax += transaction.price

    db_transaction = Transaction(
        portfolio_id=portfolio_id,
        code=transaction.code,
        trade_type=transaction.trade_type,
        quantity=transaction.quantity,
        price=transaction.price,
        commission=commission_val,
        trade_date=trade_date_val
    )
    session.add(db_transaction)
    await session.commit()
    await session.refresh(db_transaction)
    return db_transaction


@router.get("/{portfolio_id}/transactions/export")
async def export_transactions(
    portfolio_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Export transactions to CSV file"""
    from fastapi.responses import StreamingResponse

    portfolio = await session.get(Portfolio, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    result = await session.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.trade_date.desc())
    )
    transactions = result.scalars().all()

    # Build CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['code', 'trade_type', 'quantity', 'price', 'commission', 'trade_date'])
    for t in transactions:
        writer.writerow([t.code, t.trade_type, t.quantity or '', t.price, t.commission, t.trade_date])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transactions_{portfolio_id}.csv"}
    )


@router.delete("/{portfolio_id}/transactions/{transaction_id}")
async def delete_transaction(
    portfolio_id: int,
    transaction_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Delete a transaction record (does not affect positions)"""
    transaction = await session.get(Transaction, transaction_id)
    if not transaction or transaction.portfolio_id != portfolio_id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Only delete the transaction record, do not update positions
    # Position updates only happen on BUY/SELL via create_transaction
    await session.delete(transaction)
    await session.commit()
    return {"message": "Transaction deleted"}


class BatchDeleteRequest(BaseModel):
    transaction_ids: List[int]


@router.post("/{portfolio_id}/transactions/batch-delete")
async def batch_delete_transactions(
    portfolio_id: int,
    request: BatchDeleteRequest,
    session: AsyncSession = Depends(get_session)
):
    """Batch delete transaction records (does not affect positions)"""
    if not request.transaction_ids:
        return {"deleted": 0}

    result = await session.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            Transaction.id.in_(request.transaction_ids)
        )
    )
    transactions = result.scalars().all()

    for t in transactions:
        await session.delete(t)

    await session.commit()
    return {"deleted": len(transactions)}


@router.post("/{portfolio_id}/transactions/import")
async def import_transactions(
    portfolio_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Import transactions from CSV file.
    CSV format: code,trade_type,quantity,price,commission,trade_date
    trade_type: BUY, SELL, DIVIDEND, TAX
    For DIVIDEND/TAX: quantity can be empty, price is the amount
    Example: 000001,BUY,1000,10.50,5.25,2024-01-15
    Example: 000001,DIVIDEND,,100.50,0,2024-06-15
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

    valid_types = ['BUY', 'SELL', 'DIVIDEND', 'TAX']

    # Collect all rows and sort by trade_date ascending, then BUY before SELL
    # This ensures cost accumulation is correct when same-day trades exist
    def sort_key(r):
        trade_date = r.get('trade_date', '')
        trade_type = r.get('trade_type', '').strip().upper()
        # BUY=0, DIVIDEND=1, TAX=2, SELL=3 (BUY first, SELL last)
        type_order = {'BUY': 0, 'DIVIDEND': 1, 'TAX': 2, 'SELL': 3}.get(trade_type, 9)
        return (trade_date, type_order)

    rows = list(reader)
    rows.sort(key=sort_key)

    for row_num, row in enumerate(rows, start=2):
        try:
            code = row.get('code', '').strip()
            name = row.get('name', '').strip() if row.get('name') is not None else ''
            trade_type = row.get('trade_type', '').strip().upper()
            quantity_str = row.get('quantity', '').strip()
            price = float(row.get('price', 0))
            commission = float(row.get('commission', 0) or 0)
            trade_date_str = row.get('trade_date', '').strip()

            if not code or trade_type not in valid_types or price <= 0:
                errors.append(f"Row {row_num}: Invalid data")
                continue

            trade_date_val = date.fromisoformat(trade_date_str) if trade_date_str else date.today()

            # Handle BUY/SELL
            if trade_type in ['BUY', 'SELL']:
                quantity = int(quantity_str) if quantity_str else 0
                if quantity <= 0:
                    errors.append(f"Row {row_num}: quantity required for BUY/SELL")
                    continue
                try:
                    await _apply_trade_to_position(
                        session=session,
                        portfolio_id=portfolio_id,
                        code=code,
                        trade_type=trade_type,
                        quantity=quantity,
                        price=price,
                        commission=commission,
                        trade_date=trade_date_val,
                        name=name or None,
                    )
                except HTTPException as e:
                    errors.append(f"Row {row_num}: {e.detail}")
                    continue

                db_transaction = Transaction(
                    portfolio_id=portfolio_id,
                    code=code,
                    trade_type=trade_type,
                    quantity=quantity,
                    price=price,
                    commission=commission,
                    trade_date=trade_date_val
                )

            # Handle DIVIDEND/TAX
            else:
                position = await _consolidate_positions_by_code(session, portfolio_id, code)
                if not position:
                    errors.append(f"Row {row_num}: Position not found for {trade_type}")
                    continue
                if trade_type == 'DIVIDEND':
                    position.total_dividend += price
                else:  # TAX
                    position.total_tax += price

                db_transaction = Transaction(
                    portfolio_id=portfolio_id,
                    code=code,
                    trade_type=trade_type,
                    quantity=None,
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
