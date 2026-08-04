from sqlalchemy import Column, String, Integer, ForeignKey, Numeric, UniqueConstraint
from app.models.base import Base


class Department(Base):
    __tablename__ = "departments"
    
    department_id = Column(String(10), primary_key=True)
    department_name = Column(String(100), nullable=False)
    department_type = Column(String(50), nullable=False)


class Budget(Base):
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(String(10), ForeignKey("departments.department_id"), nullable=True)
    fiscal_year = Column(Integer, nullable=False)
    budget_allocation = Column(Numeric(15, 2), nullable=False)
    
    __table_args__ = (
        UniqueConstraint("department_id", "fiscal_year", name="uq_budgets_dept_year"),
    )
