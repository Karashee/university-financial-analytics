from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AnomalyResultRead(BaseModel):
    id: UUID
    transaction_id: Optional[str]
    anomaly_score: Optional[Decimal]
    is_anomaly_predicted: bool
    explanation: Optional[str]
    model_version: Optional[str]
    detected_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class ForecastResultRead(BaseModel):
    id: UUID
    department_id: Optional[str]
    fiscal_year: int
    fiscal_month: int
    predicted_expenditure: Decimal
    mae_context: Optional[Decimal]
    model_version: Optional[str]
    generated_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class BudgetUtilizationReportRead(BaseModel):
    id: int
    department_id: Optional[str]
    fiscal_year: int
    fiscal_month: int
    expenditure_category: Optional[str]
    total_transaction_amount: Optional[Decimal]
    monthly_expenditure: Optional[Decimal]
    budget_allocation: Optional[Decimal]
    utilization_percentage: Optional[Decimal]
    computed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


class TrendSummaryRead(BaseModel):
    id: int
    department_id: Optional[str]
    fiscal_year: int
    total_annual_expenditure: Optional[Decimal]
    avg_monthly_expenditure: Optional[Decimal]
    avg_growth_rate: Optional[Decimal]
    variance_from_historical_avg: Optional[Decimal]
    computed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
