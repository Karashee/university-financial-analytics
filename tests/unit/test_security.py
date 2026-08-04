"""Unit tests for security functions."""
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.config import settings


def test_hash_password_returns_different_value():
    """Test that hash_password returns a different value than input."""
    plain = "abc"
    hashed = hash_password(plain)
    assert hashed != plain


def test_verify_password_correct():
    """Test that verify_password returns True for correct password."""
    plain = "abc"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_incorrect():
    """Test that verify_password returns False for incorrect password."""
    plain = "abc"
    wrong = "wrong"
    hashed = hash_password(plain)
    assert verify_password(wrong, hashed) is False


def test_create_and_decode_token():
    """Test that token can be created and decoded successfully."""
    data = {"sub": "u1"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "u1"


def test_decode_invalid_token():
    """Test that decode_access_token returns None for invalid token."""
    invalid_token = "not.a.valid.token"
    decoded = decode_access_token(invalid_token)
    assert decoded is None


def test_decode_expired_token():
    """Test that decode_access_token returns None for expired token."""
    # Create a token that expired 5 minutes ago
    data = {"sub": "u1"}
    expire = datetime.now(timezone.utc) - timedelta(minutes=5)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    
    # Manually encode the expired token
    expired_token = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    
    # Attempt to decode - should return None
    decoded = decode_access_token(expired_token)
    assert decoded is None
