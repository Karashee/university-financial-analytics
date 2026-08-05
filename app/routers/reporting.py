"""Trend summary reporting endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.rbac import any_authenticated, finance_or_admin, get_dept_filter
from app.database import get_db
from app.models import User
from app.schemas import TrendSummaryRead
from app.services import reporting_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/compute/trend-summaries", dependencies=[finance_or_admin])
def compute_trend_summaries(db: Session = Depends(get_db)):
    """Recompute the trend summaries report from live transaction data."""
    rows_written = reporting_service.compute_trend_summaries(db)
    logger.info("Computed trend summaries: %d rows written", rows_written)
    return {"rows_written": rows_written}


@router.get("/trend-summaries", response_model=list[TrendSummaryRead])
def get_trend_summaries(
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    current_user: User = any_authenticated,
    db: Session = Depends(get_db)
):
    """List trend summaries with optional filters."""
    dept_filter = get_dept_filter(current_user)
    return reporting_service.get_trend_summaries(
        db,
        department_id=department_id,
        fiscal_year=fiscal_year,
        dept_id_filter=dept_filter,
    )
