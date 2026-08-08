"""Budget utilization analytics endpoints."""
from typing import Optional
 
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
 
from app.core.logging import get_logger
from app.core.rbac import any_authenticated, finance_or_admin, get_dept_filter
from app.database import get_db
from app.models import User
from app.schemas import BudgetUtilizationReportRead
from app.services import analytics_service
 
router = APIRouter()
logger = get_logger(__name__)
 
 
@router.post("/compute/budget-utilization", dependencies=[finance_or_admin])
def compute_budget_utilization(db: Session = Depends(get_db)):
    """Recompute the budget utilization report from live transaction/budget data."""
    rows_written = analytics_service.compute_budget_utilization(db)
    logger.info("Computed budget utilization: %d rows written", rows_written)
    return {"rows_written": rows_written}
 
 
@router.get("/budget-utilization", response_model=list[BudgetUtilizationReportRead])
def get_budget_utilization(
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_month: Optional[int] = None,
    expenditure_category: Optional[str] = None,
    current_user: User = any_authenticated,
    db: Session = Depends(get_db)
):
    """List budget utilization report rows with optional filters."""
    dept_filter = get_dept_filter(current_user)
    return analytics_service.get_budget_utilization_report(
        db,
        department_id=department_id,
        fiscal_year=fiscal_year,
        fiscal_month=fiscal_month,
        expenditure_category=expenditure_category,
        dept_id_filter=dept_filter,
    )
 
 
@router.get("/variance-report")
def get_variance_report(
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    current_user: User = any_authenticated,
    db: Session = Depends(get_db)
):
    """Per-(department_id, fiscal_year, fiscal_month) expenditure variance statistics."""
    dept_filter = get_dept_filter(current_user)
    return analytics_service.compute_variance_report(
        db,
        department_id=department_id,
        fiscal_year=fiscal_year,
        dept_id_filter=dept_filter,
    )
 
 
@router.get("/growth-rate")
def get_growth_rate(
    department_id: Optional[str] = None,
    current_user: User = any_authenticated,
    db: Session = Depends(get_db)
):
    """Per-(department_id, fiscal_year) average expenditure growth rate."""
    dept_filter = get_dept_filter(current_user)
    return analytics_service.compute_growth_rate_summary(
        db,
        department_id=department_id,
        dept_id_filter=dept_filter,
    )
 