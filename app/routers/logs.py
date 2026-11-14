"""System audit log endpoints."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.rbac import finance_or_admin
from app.database import get_db
from app.schemas.system_log import SystemLogRead
from app.services import log_service

router = APIRouter()


@router.get("", response_model=list[SystemLogRead], dependencies=[finance_or_admin])
def list_logs(
    limit: int = Query(default=50, ge=1, le=200),
    level: Optional[Literal["INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
    db: Session = Depends(get_db)
):
    """
    List the latest system log entries, newest first.

    Requires finance_officer or admin role.
    """
    return log_service.get_system_logs(db, limit=limit, level=level)
