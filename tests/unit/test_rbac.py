"""Unit tests for RBAC (Role-Based Access Control)."""
from unittest.mock import MagicMock
from fastapi import HTTPException
import pytest
from app.core.rbac import require_role, ROLE_ADMIN, ROLE_FINANCE, ROLE_DEPT_HEAD


def test_admin_passes_admin_only():
    """Test that admin user passes require_role(ROLE_ADMIN)."""
    # Create mock user with admin role
    mock_user = MagicMock()
    mock_user.role.name = ROLE_ADMIN
    
    # Get the inner function from require_role
    role_checker = require_role(ROLE_ADMIN)
    
    # Call the inner function directly
    result = role_checker(current_user=mock_user)
    
    # Should return the user
    assert result == mock_user


def test_finance_officer_fails_admin_only():
    """Test that finance_officer fails require_role(ROLE_ADMIN) with HTTP 403."""
    # Create mock user with finance_officer role
    mock_user = MagicMock()
    mock_user.role.name = ROLE_FINANCE
    
    # Get the inner function from require_role
    role_checker = require_role(ROLE_ADMIN)
    
    # Should raise HTTPException with 403
    with pytest.raises(HTTPException) as exc_info:
        role_checker(current_user=mock_user)
    
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions"


def test_multiple_roles_admin_and_finance():
    """Test require_role with multiple roles: admin passes, finance passes, dept_head raises 403."""
    # Get the inner function for admin or finance
    role_checker = require_role(ROLE_ADMIN, ROLE_FINANCE)
    
    # Test 1: Admin should pass
    mock_admin = MagicMock()
    mock_admin.role.name = ROLE_ADMIN
    result = role_checker(current_user=mock_admin)
    assert result == mock_admin
    
    # Test 2: Finance officer should pass
    mock_finance = MagicMock()
    mock_finance.role.name = ROLE_FINANCE
    result = role_checker(current_user=mock_finance)
    assert result == mock_finance
    
    # Test 3: Department head should raise 403
    mock_dept_head = MagicMock()
    mock_dept_head.role.name = ROLE_DEPT_HEAD
    with pytest.raises(HTTPException) as exc_info:
        role_checker(current_user=mock_dept_head)
    
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions"
