"""System audit log queries."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import SystemLog


def get_system_logs(
    db: Session,
    limit: int = 50,
    level: Optional[str] = None,
) -> list[SystemLog]:
    """
    Return the most recent system log entries, newest first.

    Args:
        db: Database session
        limit: Maximum number of entries to return
        level: Optional log level to filter by (INFO, WARNING, ERROR, CRITICAL)

    Returns:
        List of SystemLog rows ordered newest first
    """
    query = db.query(SystemLog)

    if level is not None:
        query = query.filter(SystemLog.level == level)

    # id breaks ties so ordering stays deterministic when two rows share a
    # timestamp - the handler writes at sub-second speed during a pipeline run.
    return (
        query.order_by(SystemLog.logged_at.desc(), SystemLog.id.desc())
        .limit(limit)
        .all()
    )
