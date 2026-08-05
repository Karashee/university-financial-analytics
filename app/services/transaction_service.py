"""Expenditure transaction services."""
from typing import Optional

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import ExpenditureTransaction
from app.schemas import TransactionCreate
from scripts.validate_csv import validate_dataframe


def _to_float(value):
    return float(value) if value is not None else None


def create_transaction(db: Session, data: TransactionCreate) -> ExpenditureTransaction:
    """
    Create a single expenditure transaction from manual entry.

    Applies the same 5 validation rules used for CSV ingestion (via
    validate_dataframe on a single-row DataFrame, no file I/O). Raises
    HTTP 422 with {"rule": ..., "detail": ...} on rule failure, HTTP 409
    on duplicate transaction_id.
    """
    row = {
        "Transaction_ID": data.transaction_id,
        "Department_ID": data.department_id,
        "Fiscal_Year": data.fiscal_year,
        "Fiscal_Month": data.fiscal_month,
        "Transaction_Date": data.transaction_date,
        "Monthly_Expenditure": _to_float(data.monthly_expenditure),
        "Transaction_Amount": _to_float(data.transaction_amount),
        "Expenditure_Category": data.expenditure_category,
        "Budget_Utilization_Percentage": _to_float(data.budget_utilization_percentage),
        "Expenditure_Variance": _to_float(data.expenditure_variance),
        "Historical_Average_Expenditure": _to_float(data.historical_average_expenditure),
    }
    df = pd.DataFrame([row])
    validation = validate_dataframe(df)
    if validation["rejected_count"] > 0:
        rejected = validation["rejected_rows"][0]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"rule": rejected["rule"], "detail": rejected["detail"]}
        )

    existing = db.get(ExpenditureTransaction, data.transaction_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transaction already exists"
        )

    transaction = ExpenditureTransaction(
        transaction_id=data.transaction_id,
        department_id=data.department_id,
        fiscal_year=data.fiscal_year,
        fiscal_month=data.fiscal_month,
        transaction_date=data.transaction_date,
        monthly_expenditure=data.monthly_expenditure,
        transaction_amount=data.transaction_amount,
        expenditure_category=data.expenditure_category,
        vendor_category=data.vendor_category,
        budget_utilization_percentage=data.budget_utilization_percentage,
        expenditure_variance=data.expenditure_variance,
        historical_average_expenditure=data.historical_average_expenditure,
        expenditure_growth_rate=data.expenditure_growth_rate,
        is_anomaly_ground_truth=data.is_anomaly_ground_truth if data.is_anomaly_ground_truth is not None else 0,
        anomaly_type_ground_truth=data.anomaly_type_ground_truth if data.anomaly_type_ground_truth is not None else "Normal",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transactions(
    db: Session,
    department_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_month: Optional[int] = None,
    expenditure_category: Optional[str] = None,
    vendor_category: Optional[str] = None,
    is_anomaly: Optional[int] = None,
    dept_id_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> list[ExpenditureTransaction]:
    """
    Query transactions with optional filters.

    dept_id_filter, when not None, is a mandatory department_id filter that
    overrides the optional department_id parameter (used to enforce
    department_head row-level access).
    """
    query = db.query(ExpenditureTransaction)

    if dept_id_filter is not None:
        query = query.filter(ExpenditureTransaction.department_id == dept_id_filter)
    elif department_id is not None:
        query = query.filter(ExpenditureTransaction.department_id == department_id)

    if fiscal_year is not None:
        query = query.filter(ExpenditureTransaction.fiscal_year == fiscal_year)
    if fiscal_month is not None:
        query = query.filter(ExpenditureTransaction.fiscal_month == fiscal_month)
    if expenditure_category is not None:
        query = query.filter(ExpenditureTransaction.expenditure_category == expenditure_category)
    if vendor_category is not None:
        query = query.filter(ExpenditureTransaction.vendor_category == vendor_category)
    if is_anomaly is not None:
        query = query.filter(ExpenditureTransaction.is_anomaly_ground_truth == is_anomaly)

    return query.offset(skip).limit(limit).all()


def get_transaction(db: Session, transaction_id: str) -> Optional[ExpenditureTransaction]:
    """Get a single transaction by ID."""
    return db.get(ExpenditureTransaction, transaction_id)
