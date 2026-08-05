"""Isolation Forest anomaly detection endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.rbac import any_authenticated, finance_or_admin, get_dept_filter
from app.database import get_db
from app.models import User
from app.services import anomaly_service

router = APIRouter()


@router.post("/detect", dependencies=[finance_or_admin])
def detect_anomalies(db: Session = Depends(get_db)):
    """Retrain the Isolation Forest on all transactions and rescore every row."""
    return anomaly_service.run_anomaly_detection(db)


@router.get("/results")
def get_anomaly_results(
    is_anomaly_predicted: Optional[bool] = None,
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    current_user: User = any_authenticated,
    db: Session = Depends(get_db)
):
    """List anomaly detection results with optional filters."""
    dept_filter = get_dept_filter(current_user)
    return anomaly_service.get_anomaly_results(
        db,
        is_anomaly_predicted=is_anomaly_predicted,
        department_id=department_id,
        fiscal_year=fiscal_year,
        dept_id_filter=dept_filter,
    )
