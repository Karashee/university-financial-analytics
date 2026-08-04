from uuid import UUID
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role_id: int
    department_id: Optional[str] = None


class UserRead(BaseModel):
    id: UUID
    username: str
    email: str
    role_id: int
    is_active: bool
    department_id: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
