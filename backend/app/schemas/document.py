from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class TableData(BaseModel):
    """Structured tabular data for spreadsheets, CSVs, and DOCX tables."""
    headers: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)


class SectionContent(BaseModel):
    """Represents a discrete section (page, sheet, or structured block)."""
    type: str  # "page", "sheet", "text", "table"
    index: int
    title: str
    content: Optional[str] = None
    table: Optional[TableData] = None


class ExtractionResult(BaseModel):
    """Complete structured extraction payload for a document."""
    document_id: str
    filename: str
    file_type: str
    status: str  # "completed", "warning", "failed"
    has_text: bool = True
    total_pages: int = 0
    total_sheets: int = 0
    total_words: int = 0
    warnings: List[str] = Field(default_factory=list)
    sections: List[SectionContent] = Field(default_factory=list)
    raw_preview: str = ""


class DocumentSummary(BaseModel):
    """Summary of document metadata and processing status."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: Optional[str] = None
    original_filename: str
    file_type: str
    file_size_bytes: int
    extraction_status: str
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    total_pages: Optional[int] = 0
    total_sheets: Optional[int] = 0
    total_words: Optional[int] = 0
    has_text: bool = True
    created_at: datetime


class DocumentDetail(DocumentSummary):
    """Full detail of a document including its structured extraction content."""
    extraction: Optional[ExtractionResult] = None
