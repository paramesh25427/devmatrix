from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ConfidenceLevel(str, Enum):
    """
    Confidence scoring rules:
    - HIGH: Explicitly declared in document with unambiguous direct textual evidence.
    - MEDIUM: Derived or synthesized from contextual clues across multiple statements.
    - LOW: Inferred, speculative, ambiguous, or lacks specific quantifiable detail.
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceReference(BaseModel):
    """Explicit provenance citation for an extracted item."""
    source_type: str = Field(description="Type of source marker: 'page', 'sheet', 'table', or 'section'")
    location: str = Field(description="Human-readable location, e.g., 'Page 2', 'Sheet: Milestones, Row 3', 'Section 1'")
    excerpt: Optional[str] = Field(default=None, description="Exact quotation or short phrase from the document text")


class RequirementItem(BaseModel):
    """Individual functional or non-functional requirement specification."""
    id: str = Field(description="Stable requirement identifier, e.g., 'FR-01' or 'NFR-01'")
    title: str = Field(description="Concise requirement title")
    description: str = Field(description="Detailed functional or behavioral specification")
    category: str = Field(description="Functional domain, e.g., 'Core Platform', 'Security', 'Performance', 'Integrations'")
    source_references: List[SourceReference] = Field(
        default_factory=list,
        description="List of exact provenance references verifying this requirement",
    )
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.MEDIUM,
        description="Confidence assessment based on explicit evidence",
    )
    needs_verification: bool = Field(
        default=False,
        description="True if requirement is inferred, ambiguous, or requires stakeholder signoff",
    )
    verification_reason: Optional[str] = Field(
        default=None,
        description="Explicit explanation of why human verification or clarification is needed",
    )


class RiskItem(BaseModel):
    """Potential technical, operational, or delivery risk identified in document."""
    id: str = Field(description="Stable identifier, e.g., 'RSK-01'")
    description: str = Field(description="Description of the risk")
    severity: str = Field(description="Severity impact: 'high', 'medium', or 'low'")
    mitigation_hint: Optional[str] = Field(default=None, description="Suggested mitigation or preventive strategy")
    source_reference: Optional[SourceReference] = Field(default=None, description="Document reference that triggered risk")


class MissingInfoItem(BaseModel):
    """Critical information omitted from intake documents requiring clarification."""
    id: str = Field(description="Stable identifier, e.g., 'Q-01'")
    topic: str = Field(description="Domain area, e.g., 'Authentication Provider', 'Deployment Target', 'SLAs'")
    question: str = Field(description="Clarification question for project stakeholders")
    impact: str = Field(description="Impact of missing information: 'high', 'medium', or 'low'")


class ProjectScope(BaseModel):
    """Scope boundaries and tangible deliverables."""
    deliverables: List[str] = Field(default_factory=list, description="Explicit output deliverables")
    scope_inclusions: List[str] = Field(default_factory=list, description="Items explicitly declared in-scope")
    scope_exclusions: List[str] = Field(default_factory=list, description="Items explicitly declared out-of-scope")


class ProjectRequirementsData(BaseModel):
    """
    Validated structured project requirements payload.
    Identical Pydantic validation rules apply to all AI providers.
    """
    model_config = ConfigDict(extra="ignore")

    project_summary: str = Field(description="Executive narrative summary of the project intake")
    objectives: List[str] = Field(default_factory=list, description="Primary business or technical goals")
    scope: ProjectScope = Field(default_factory=ProjectScope)
    functional_requirements: List[RequirementItem] = Field(default_factory=list)
    non_functional_requirements: List[RequirementItem] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list, description="Technical, regulatory, or business constraints")
    dependencies: List[str] = Field(default_factory=list, description="External systems or preceding project prerequisites")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made by stakeholders or intake team")
    risks: List[RiskItem] = Field(default_factory=list)
    missing_information: List[MissingInfoItem] = Field(
        default_factory=list,
        description="Information gaps requiring stakeholder answers; never treated as confirmed facts",
    )
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized overall extraction confidence between 0.0 and 1.0",
    )
    uncertainty_notes: List[str] = Field(
        default_factory=list,
        description="Summary of ambiguous or unverified elements",
    )


class ProviderAttemptLog(BaseModel):
    """Operational telemetry for fallback auditing without exposing sensitive content or keys."""
    provider: str
    model: str
    duration_ms: int
    attempt_count: int
    status: str  # "success", "rate_limited", "timeout", "auth_error", "validation_error", "server_error", "skipped"
    error_category: Optional[str] = None


class RequirementDraftResponse(BaseModel):
    """Public API response representing an AI-generated draft awaiting manager review."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    document_name: str
    provider_used: str
    model_used: str
    status: str  # "draft_ready", "failed"
    review_status: str  # "pending_review", "approved", "rejected"
    manager_notes: Optional[str] = None
    attempt_history: List[ProviderAttemptLog] = Field(default_factory=list)
    requirements: Optional[ProjectRequirementsData] = None
    created_at: datetime
    updated_at: datetime


class ReviewUpdateRequest(BaseModel):
    """Manager review decision submission."""
    review_status: str = Field(description="'approved', 'rejected', or 'pending_review'")
    manager_notes: Optional[str] = Field(default=None, description="Manager review feedback or notes")
