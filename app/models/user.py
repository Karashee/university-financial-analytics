from uuid import uuid4
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        server_default=text("uuid_generate_v4()"),
        default=uuid4
    )
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    department_id = Column(String(10), ForeignKey("departments.department_id"), nullable=True)
    is_active = Column(Boolean, server_default="true", default=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), default=func.now)
    
    # Relationships
    role = relationship("Role")
    department = relationship("Department")
