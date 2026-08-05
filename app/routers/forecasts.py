"""Linear Regression expenditure forecast endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import any_authenticated, finance_or_admin, get_dept_filter
from app.database import get_db
from app.models import User
from app.services import forecast_service

router = APIRouter()


@router.post("/run", dependencies=[finance_or_admin])
def run_forecast(n_months: int = 3, db: Session = Depends(get_db)):
    """Retrain the LR model and generate expenditure forecasts n_months ahead."""
    if not (1 <= n_months <= 12):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="n_months must be between 1 and 12"
        )
    return forecast_service.run_expenditure_forecast(db, n_months=n_months)


@router.get("")
def get_forecasts(
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    current_user: User = any_authenticated,
    db: Session = Depends(get_db)
):
    """List forecast results with optional filters."""
    dept_filter = get_dept_filter(current_user)
    return forecast_service.get_forecast_results(
        db,
        department_id=department_id,
        fiscal_year=fiscal_year,
        dept_id_filter=dept_filter,
    )
