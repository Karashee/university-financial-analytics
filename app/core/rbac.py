"""Role-Based Access Control (RBAC) utilities."""
from typing import Callable, Optional
from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user
from app.models import User

# Role name constants - define once, import everywhere
ROLE_ADMIN = "admin"
ROLE_FINANCE = "finance_officer"
ROLE_DEPT_HEAD = "department_head"


def require_role(*roles: str) -> Callable:
    """
    Create a FastAPI dependency that requires specific roles.
    
    Args:
        *roles: One or more role names that are allowed
        
    Returns:
        FastAPI dependency function that validates user role
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """Inner function that checks if user has required role."""
        if current_user.role.name not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    return role_checker


# Pre-built role dependencies for common use cases
admin_only = Depends(require_role(ROLE_ADMIN))
finance_or_admin = Depends(require_role(ROLE_ADMIN, ROLE_FINANCE))
any_authenticated = Depends(require_role(ROLE_ADMIN, ROLE_FINANCE, ROLE_DEPT_HEAD))


def get_dept_filter(current_user: User) -> Optional[str]:
    """
    Get department filter for the current user.
    
    Department heads can only see their own department's data.
    Other roles can see all departments.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        department_id if user is a department head, None otherwise
    """
    if current_user.role.name == ROLE_DEPT_HEAD:
        return current_user.department_id
    return None
