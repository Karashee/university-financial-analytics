from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TransactionCreate(BaseModel):
    transaction_id: str
    department_id: str
    fiscal_year: int
    fiscal_month: int
    transaction_date: date
    transaction_amount: Decimal
    expenditure_category: str
    vendor_category: str
    monthly_expenditure: Optional[Decimal] = None
    budget_utilization_percentage: Optional[Decimal] = None
    expenditure_variance: Optional[Decimal] = None
    historical_average_expenditure: Optional[Decimal] = None
    expenditure_growth_rate: Optional[Decimal] = None
    is_anomaly_ground_truth: Optional[int] = None
    anomaly_type_ground_truth: Optional[str] = None


class TransactionRead(BaseModel):
    transaction_id: str
    department_id: str
    fiscal_year: int
    fiscal_month: int
    transaction_date: date
    monthly_expenditure: Optional[Decimal]
    transaction_amount: Decimal
    expenditure_category: str
    vendor_category: str
    budget_utilization_percentage: Optional[Decimal]
    expenditure_variance: Optional[Decimal]
    historical_average_expenditure: Optional[Decimal]
    expenditure_growth_rate: Optional[Decimal]
    is_anomaly_ground_truth: Optional[int]
    anomaly_type_ground_truth: Optional[str]
    created_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)
