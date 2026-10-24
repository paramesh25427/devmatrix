import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean
from app.core.database import Base


class Document(Base):
    """SQLAlchemy model for uploaded project documents."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, default="tenant-default", index=True)
    project_id = Column(String(36), nullable=True, index=True)

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_type = Column(String(20), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=True)
    content_hash = Column(String(64), nullable=True)

    extraction_status = Column(String(30), nullable=False, default="pending")  # pending, completed, warning, failed
    error_message = Column(Text, nullable=True)
    warning_message = Column(Text, nullable=True)

    total_pages = Column(Integer, nullable=True, default=0)
    total_sheets = Column(Integer, nullable=True, default=0)
    total_words = Column(Integer, nullable=True, default=0)
    has_text = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
