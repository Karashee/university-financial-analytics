from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.database import get_db
from app.schemas import Token
from app.core.security import verify_password, create_access_token
from app.services import user_service

router = APIRouter()
logger = get_logger(__name__)


@router.post("/token", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 compatible token login endpoint.
    
    Args:
        form_data: OAuth2 form with username and password
        db: Database session
        
    Returns:
        Token with access_token and token_type
        
    Raises:
        HTTPException: 401 if credentials are incorrect
    """
    # Query user by username using user_service
    user = user_service.get_user_by_username(db, form_data.username)
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login attempt for username=%s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token = create_access_token(data={"sub": str(user.id)})
    logger.info("User %s logged in successfully", user.username)

    return {"access_token": access_token, "token_type": "bearer"}
