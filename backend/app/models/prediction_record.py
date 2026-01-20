"""Prediction record database model"""
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class PredictionRecord(SQLModel, table=True):
    """Prediction record"""
    __tablename__ = "prediction_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_name: str = Field(max_length=50, description="Stock name")
    stock_code: str = Field(max_length=10, index=True, description="Stock code")
    forward_days: int = Field(description="Prediction horizon (days)")
    current_price: Optional[float] = Field(default=None, description="Current price")
    direction: str = Field(max_length=20, description="Direction prediction")
    signal: str = Field(max_length=20, description="Trading signal")
    recommendation: str = Field(max_length=20, description="Recommendation")
    expected_price: Optional[float] = Field(default=None, description="Expected price")
    support: Optional[float] = Field(default=None, description="Support level")
    resistance: Optional[float] = Field(default=None, description="Resistance level")
    prediction_date: str = Field(max_length=10, description="Prediction date")
    accuracy: str = Field(default="unknown", max_length=20, description="Accuracy status")
    created_at: datetime = Field(default_factory=datetime.now)
