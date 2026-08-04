"""User service for user management operations."""
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import User, Role
from app.core.security import hash_password
from app.core.rbac import ROLE_DEPT_HEAD


def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    role_id: int,
    department_id: Optional[str] = None
) -> User:
    """
    Create a new user.
    
    Args:
        db: Database session
        username: Username
        email: Email address
        password: Plain text password (will be hashed)
        role_id: Role ID
        department_id: Department ID (optional, required for department heads)
        
    Returns:
        Created User object
        
    Raises:
        HTTPException: 400 if role_id is invalid
        HTTPException: 422 if department_head user missing department_id
    """
    # Step 1: Look up Role by role_id
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role_id"
        )
    
    # Step 2: Validate department_id for department heads
    if role.name == ROLE_DEPT_HEAD and department_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="department_head users must have a department_id"
        )
    
    # Step 3: Hash password and create user
    hashed_password = hash_password(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        role_id=role_id,
        department_id=department_id,
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Get a user by username.
    
    Args:
        db: Database session
        username: Username to search for
        
    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """
    Get a user by ID.
    
    Args:
        db: Database session
        user_id: User ID (UUID)
        
    Returns:
        User object if found, None otherwise
    """
    return db.query(User).filter(User.id == user_id).first()


def list_users(db: Session) -> list[User]:
    """
    List all users.
    
    Args:
        db: Database session
        
    Returns:
        List of User objects
    """
    return db.query(User).all()
