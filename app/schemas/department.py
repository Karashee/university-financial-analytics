from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class DepartmentCreate(BaseModel):
    department_id: str
    department_name: str
    department_type: str


class DepartmentRead(BaseModel):
    department_id: str
    department_name: str
    department_type: str
    
    model_config = ConfigDict(from_attributes=True)


class BudgetCreate(BaseModel):
    department_id: str
    fiscal_year: int
    budget_allocation: Decimal


class BudgetRead(BaseModel):
    id: int
    department_id: str
    fiscal_year: int
    budget_allocation: Decimal
    
    model_config = ConfigDict(from_attributes=True)
