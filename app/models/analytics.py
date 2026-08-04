from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text, func
from app.models.base import Base


class AnomalyResult(Base):
    __tablename__ = "anomaly_results"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("uuid_generate_v4()"),
        default=uuid4
    )
    transaction_id = Column(String(20), ForeignKey("expenditure_transactions.transaction_id"), nullable=True)
    anomaly_score = Column(Numeric(12, 8), nullable=True)
    is_anomaly_predicted = Column(Boolean, nullable=False)
    explanation = Column(String(500), nullable=True)
    model_version = Column(String(50), nullable=True)
    detected_at = Column(TIMESTAMP, server_default=func.now(), default=func.now)


class ForecastResult(Base):
    __tablename__ = "forecast_results"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("uuid_generate_v4()"),
        default=uuid4
    )
    department_id = Column(String(10), ForeignKey("departments.department_id"), nullable=True)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_month = Column(Integer, nullable=False)
    predicted_expenditure = Column(Numeric(15, 2), nullable=False)
    mae_context = Column(Numeric(15, 2), nullable=True)
    model_version = Column(String(50), nullable=True)
    generated_at = Column(TIMESTAMP, server_default=func.now(), default=func.now)


class BudgetUtilizationReport(Base):
    __tablename__ = "budget_utilization_report"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(String(10), ForeignKey("departments.department_id"), nullable=True)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_month = Column(Integer, nullable=False)
    expenditure_category = Column(String(100), nullable=True)
    total_transaction_amount = Column(Numeric(15, 2), nullable=True)
    monthly_expenditure = Column(Numeric(15, 2), nullable=True)
    budget_allocation = Column(Numeric(15, 2), nullable=True)
    utilization_percentage = Column(Numeric(8, 4), nullable=True)
    computed_at = Column(TIMESTAMP, server_default=func.now(), default=func.now)


class TrendSummary(Base):
    __tablename__ = "trend_summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(String(10), ForeignKey("departments.department_id"), nullable=True)
    fiscal_year = Column(Integer, nullable=False)
    total_annual_expenditure = Column(Numeric(15, 2), nullable=True)
    avg_monthly_expenditure = Column(Numeric(15, 2), nullable=True)
    avg_growth_rate = Column(Numeric(10, 4), nullable=True)
    variance_from_historical_avg = Column(Numeric(15, 2), nullable=True)
    computed_at = Column(TIMESTAMP, server_default=func.now(), default=func.now)
