"""ORM model for the application audit log."""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.models.base import Base


class SystemLog(Base):
    """
    Application log records persisted for the audit trail.

    Mirrors alembic revision 0005 exactly (columns and index names) so the
    SQLite test database can create this table from the model metadata
    instead of running the PostgreSQL migrations.
    """

    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    logged_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=func.now(),
        index=True,
    )
    level = Column(String(20), nullable=False, index=True)
    logger_name = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(120), nullable=True)
    function_name = Column(String(120), nullable=True)
    line_number = Column(Integer, nullable=True)
