"""Prediction record API endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.prediction_record import PredictionRecord

router = APIRouter()


class PredictionRecordCreate(BaseModel):
    stock_name: str
    stock_code: str
    forward_days: int
    current_price: Optional[float] = None
    direction: str
    signal: str
    recommendation: str
    expected_price: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    prediction_date: str
    accuracy: str = Field(default="unknown", pattern="^(unknown|accurate|inaccurate)$")


class PredictionRecordUpdate(BaseModel):
    accuracy: str = Field(..., pattern="^(unknown|accurate|inaccurate)$")


@router.get("/", response_model=List[PredictionRecord])
async def list_prediction_records(
    limit: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PredictionRecord)
        .order_by(PredictionRecord.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=PredictionRecord)
async def create_prediction_record(
    payload: PredictionRecordCreate,
    session: AsyncSession = Depends(get_session),
):
    record = PredictionRecord(**payload.model_dump())
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


@router.patch("/{record_id}", response_model=PredictionRecord)
async def update_prediction_record(
    record_id: int,
    payload: PredictionRecordUpdate,
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(PredictionRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Prediction record not found")

    record.accuracy = payload.accuracy
    await session.commit()
    await session.refresh(record)
    return record


@router.delete("/{record_id}")
async def delete_prediction_record(
    record_id: int,
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(PredictionRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Prediction record not found")

    await session.delete(record)
    await session.commit()
    return {"message": "Prediction record deleted"}
