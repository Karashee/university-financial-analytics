from sqlalchemy import Column, String, Integer, Date, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.models.base import Base


class ExpenditureTransaction(Base):
    __tablename__ = "expenditure_transactions"
    
    transaction_id = Column(String(20), primary_key=True)
    department_id = Column(String(10), ForeignKey("departments.department_id"), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_month = Column(Integer, nullable=False)
    transaction_date = Column(Date, nullable=False)
    monthly_expenditure = Column(Numeric(15, 2), nullable=True)
    transaction_amount = Column(Numeric(15, 2), nullable=False)
    expenditure_category = Column(String(100), nullable=False)
    vendor_category = Column(String(100), nullable=False)
    budget_utilization_percentage = Column(Numeric(8, 4), nullable=True)
    expenditure_variance = Column(Numeric(15, 2), nullable=True)
    historical_average_expenditure = Column(Numeric(15, 2), nullable=True)
    expenditure_growth_rate = Column(Numeric(10, 4), nullable=True)
    is_anomaly_ground_truth = Column(Integer, server_default="0", default=0)
    anomaly_type_ground_truth = Column(String(100), server_default="'Normal'", default="Normal")
    created_at = Column(TIMESTAMP, server_default=func.now(), default=func.now)
