"""Expenditure transaction endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.rbac import any_authenticated, finance_or_admin, get_dept_filter
from app.database import get_db
from app.models import User
from app.schemas import TransactionCreate, TransactionRead
from app.services import transaction_service

router = APIRouter()


@router.post("", response_model=TransactionRead, dependencies=[finance_or_admin])
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    """Create a transaction from manual entry. Requires finance_officer or admin role."""
    return transaction_service.create_transaction(db, data)


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_month: Optional[int] = None,
    expenditure_category: Optional[str] = None,
    vendor_category: Optional[str] = None,
    is_anomaly: Optional[int] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    current_user: User = any_authenticated,
    db: Session = Depends(get_db)
):
    """
    List transactions with optional filters.

    department_head users only see rows from their own department, enforced
    via get_dept_filter regardless of the department_id query parameter.
    """
    dept_filter = get_dept_filter(current_user)
    return transaction_service.get_transactions(
        db,
        department_id=department_id,
        fiscal_year=fiscal_year,
        fiscal_month=fiscal_month,
        expenditure_category=expenditure_category,
        vendor_category=vendor_category,
        is_anomaly=is_anomaly,
        dept_id_filter=dept_filter,
        skip=skip,
        limit=limit,
    )


@router.get("/{transaction_id}", response_model=TransactionRead, dependencies=[any_authenticated])
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    """Get a single transaction by ID."""
    transaction = transaction_service.get_transaction(db, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction
