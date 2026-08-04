"""User management endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserCreate, UserRead
from app.services import user_service
from app.core.rbac import admin_only
from app.models import User

router = APIRouter()


@router.post("", response_model=UserRead, dependencies=[admin_only])
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    
    Requires admin role.
    
    Args:
        user_data: User creation data
        db: Database session
        
    Returns:
        Created user data
    """
    user = user_service.create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        role_id=user_data.role_id,
        department_id=user_data.department_id
    )
    return user


@router.get("", response_model=list[UserRead], dependencies=[admin_only])
def list_users(db: Session = Depends(get_db)):
    """
    List all users.
    
    Requires admin role.
    
    Args:
        db: Database session
        
    Returns:
        List of users
    """
    users = user_service.list_users(db)
    return users
