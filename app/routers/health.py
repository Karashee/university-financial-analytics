from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint that verifies database connectivity.
    
    Returns:
        dict: Status and database connection state
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        # Don't raise, just report database as unavailable
        return {"status": "ok", "database": "unavailable"}
