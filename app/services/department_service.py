"""Department, budget, and lookup services."""
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Budget, Department


def create_department(db: Session, department_id: str, name: str, type: str) -> Department:
    """Create a new department. Raises HTTP 409 if the ID already exists."""
    existing = db.get(Department, department_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department already exists"
        )

    department = Department(
        department_id=department_id,
        department_name=name,
        department_type=type,
    )
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def create_budget(
    db: Session,
    department_id: str,
    fiscal_year: int,
    budget_allocation: Decimal
) -> Budget:
    """
    Create a budget for a department/fiscal year.

    Raises HTTP 404 if the department does not exist, HTTP 409 if a budget
    for this (department_id, fiscal_year) already exists.
    """
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found"
        )

    existing = (
        db.query(Budget)
        .filter(Budget.department_id == department_id, Budget.fiscal_year == fiscal_year)
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget already exists for this department and fiscal year"
        )

    budget = Budget(
        department_id=department_id,
        fiscal_year=fiscal_year,
        budget_allocation=budget_allocation,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


def get_all_departments(db: Session, department_type: Optional[str] = None) -> list[Department]:
    """List departments, optionally filtered by department_type."""
    query = db.query(Department)
    if department_type is not None:
        query = query.filter(Department.department_type == department_type)
    return query.all()


def get_department(db: Session, department_id: str) -> Optional[Department]:
    """Get a single department by ID."""
    return db.get(Department, department_id)


def get_budgets(db: Session, fiscal_year: Optional[int] = None) -> list[Budget]:
    """List budgets, optionally filtered by fiscal_year."""
    query = db.query(Budget)
    if fiscal_year is not None:
        query = query.filter(Budget.fiscal_year == fiscal_year)
    return query.all()
