"""Department and budget endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.rbac import admin_only, any_authenticated, finance_or_admin
from app.database import get_db
from app.schemas import BudgetCreate, BudgetRead, DepartmentCreate, DepartmentRead
from app.services import department_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/departments", response_model=DepartmentRead, dependencies=[admin_only])
def create_department(data: DepartmentCreate, db: Session = Depends(get_db)):
    """Create a new department. Requires admin role."""
    department = department_service.create_department(
        db,
        department_id=data.department_id,
        name=data.department_name,
        type=data.department_type,
    )
    logger.info("Created department %s", department.department_id)
    return department


@router.post("/departments/{department_id}/budgets", response_model=BudgetRead, dependencies=[finance_or_admin])
def create_budget(department_id: str, data: BudgetCreate, db: Session = Depends(get_db)):
    """Create a budget for a department/fiscal year. Requires finance_officer or admin role."""
    budget = department_service.create_budget(
        db,
        department_id=department_id,
        fiscal_year=data.fiscal_year,
        budget_allocation=data.budget_allocation,
    )
    logger.info("Created budget for %s fiscal_year=%s", department_id, data.fiscal_year)
    return budget


@router.get("/departments", response_model=list[DepartmentRead], dependencies=[any_authenticated])
def list_departments(type: Optional[str] = None, db: Session = Depends(get_db)):
    """List departments, optionally filtered by type."""
    return department_service.get_all_departments(db, department_type=type)


@router.get("/departments/{department_id}", response_model=DepartmentRead, dependencies=[any_authenticated])
def get_department(department_id: str, db: Session = Depends(get_db)):
    """Get a single department by ID."""
    department = department_service.get_department(db, department_id)
    if department is None:
        logger.warning("Department not found: %s", department_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return department


@router.get("/budgets", response_model=list[BudgetRead], dependencies=[any_authenticated])
def list_budgets(fiscal_year: Optional[int] = None, db: Session = Depends(get_db)):
    """List budgets, optionally filtered by fiscal_year."""
    return department_service.get_budgets(db, fiscal_year=fiscal_year)
