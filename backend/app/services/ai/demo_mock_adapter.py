import re
import json
from typing import List, Tuple
from app.schemas.document import ExtractionResult
from app.schemas.requirement import (
    ProjectRequirementsData,
    ProjectScope,
    RequirementItem,
    RiskItem,
    MissingInfoItem,
    SourceReference,
    ConfidenceLevel,
    ProviderAttemptLog,
)
from app.services.ai.base import BaseAIAdapter


class DemoMockAIAdapter(BaseAIAdapter):
    """
    High-fidelity offline extraction adapter.
    Enables complete demonstration, deterministic workflows, and tests
    without requiring external cloud AI credentials or incurring live API costs.
    """

    @property
    def provider_name(self) -> str:
        return "DevMatrix Offline Deterministic Engine"

    @property
    def model_name(self) -> str:
        return "devmatrix-deterministic-extractor-v1"

    @property
    def is_configured(self) -> bool:
        return True

    async def generate_json_text(self, system_instruction: str, user_prompt: str) -> str:
        """Returns mock JSON response string."""
        return "{}"

    def generate_deterministic_requirements(
        self,
        extraction: ExtractionResult,
    ) -> ProjectRequirementsData:
        """Deterministically extracts candidate requirements, conflicts, and questions from text."""
        all_text = ""
        for sec in extraction.sections:
            if sec.content:
                all_text += " " + sec.content

        words = all_text.split()
        title = extraction.filename.rsplit(".", 1)[0].replace("_", " ").title()

        # Detect budget mentions
        budget_matches = re.findall(r"\$\s?[\d,]+(?:\.\d+)?", all_text)
        detected_budget = budget_matches[0] if budget_matches else "$250,000 USD"

        # Detect deadline mentions
        date_matches = re.findall(r"\b(?:202[4-9]|Q[1-4]\s*202[4-9]|December\s*\d{1,2}|January\s*\d{1,2})\b", all_text)
        detected_deadline = date_matches[0] if date_matches else "Q4 2026"

        source_ref = SourceReference(
            source_type="section",
            location="Section: Overview & Specification",
            excerpt=all_text[:120] if all_text else "Document intake content",
        )

        functional = [
            RequirementItem(
                id="FR-01",
                title="Role-Based Access Control & Session Management",
                description="The system must enforce granular role-based access control with token expiration and tenant isolation.",
                category="Security & Access",
                source_references=[source_ref],
                confidence=ConfidenceLevel.HIGH,
                needs_verification=False,
            ),
            RequirementItem(
                id="FR-02",
                title="Multi-Format Streaming Document Ingestion",
                description="The platform must accept PDF, DOCX, XLSX, and CSV documents, perform magic-byte validation, and parse tabular content.",
                category="Intake & Extraction",
                source_references=[source_ref],
                confidence=ConfidenceLevel.HIGH,
                needs_verification=False,
            ),
            RequirementItem(
                id="FR-03",
                title="Deterministic PERT Work Breakdown & Schedule Engine",
                description="Generate three-point effort estimates and compute critical path schedule using CPM algorithms.",
                category="Planning & Estimation",
                source_references=[source_ref],
                confidence=ConfidenceLevel.HIGH,
                needs_verification=False,
            ),
            RequirementItem(
                id="FR-04",
                title="Executive Delivery Report Export in PDF",
                description="Compile approved requirements, WBS schedule, rate-card costs, and risk heat maps into downloadable PDF reports.",
                category="Reporting & Governance",
                source_references=[source_ref],
                confidence=ConfidenceLevel.HIGH,
                needs_verification=False,
            ),
        ]

        non_functional = [
            RequirementItem(
                id="NFR-01",
                title="Tenant Data Segregation and Encryption at Rest",
                description="All persistent tenant records and uploaded artifacts must be segregated by tenant ID and encrypted.",
                category="Compliance & Privacy",
                source_references=[source_ref],
                confidence=ConfidenceLevel.HIGH,
                needs_verification=False,
            ),
            RequirementItem(
                id="NFR-02",
                title="Sub-Second Interactive API Response Latency",
                description="All interactive REST endpoints must respond within 500ms under standard operational load.",
                category="Performance & Scalability",
                source_references=[source_ref],
                confidence=ConfidenceLevel.HIGH,
                needs_verification=False,
            ),
        ]

        risks = [
            RiskItem(
                id="RSK-01",
                description="Third-party cloud API outages or rate limit spikes may delay extraction if not handled.",
                severity="high",
                mitigation_hint="Implement multi-provider fallback and deterministic local processing.",
                source_reference=source_ref,
            ),
            RiskItem(
                id="RSK-02",
                description="Delay in managerial baseline review may defer downstream sprint planning.",
                severity="medium",
                mitigation_hint="Configure automatic escalation alerts for pending approvals.",
                source_reference=source_ref,
            ),
        ]

        missing_info = [
            MissingInfoItem(
                id="Q-01",
                topic="Authentication Infrastructure",
                question="Should Single Sign-On (SSO) integrate with corporate SAML 2.0 or OpenID Connect (OIDC)?",
                impact="high",
            ),
            MissingInfoItem(
                id="Q-02",
                topic="Deployment Cloud Target",
                question="What is the primary AWS/Azure cloud region and disaster recovery RTO/RPO target?",
                impact="medium",
            ),
        ]

        scope = ProjectScope(
            deliverables=[
                "Validated Requirements Baseline",
                "Work Breakdown Structure with Critical Path",
                "Effort, Cost and Schedule Estimate",
                "Feasibility and Risk Register",
                "Executive Delivery Plan PDF",
            ],
            scope_inclusions=[
                "Document ingestion and structured text/table extraction",
                "Multi-criteria workforce recommendation",
                "Delivery progress and milestone tracking",
            ],
            scope_exclusions=[
                "Automated employment termination or unreviewed hiring decisions",
                "Intrusive employee surveillance (keystroke, webcam, mouse tracking)",
            ],
        )

        return ProjectRequirementsData(
            project_summary=f"Delivery plan for '{title}' derived from {len(words)} extracted words across {len(extraction.sections)} document sections.",
            objectives=[
                "Modernize enterprise project delivery through structured AI assistance",
                "Establish deterministic, reviewable effort, cost, and schedule baselines",
                "Ensure transparent workforce recommendations without intrusive surveillance",
            ],
            scope=scope,
            functional_requirements=functional,
            non_functional_requirements=non_functional,
            constraints=[
                f"Target delivery budget constrained to {detected_budget}",
                f"Target completion milestone planned for {detected_deadline}",
            ],
            dependencies=[
                "Corporate identity provider directory",
                "Enterprise cloud hosting environment",
            ],
            assumptions=[
                "Standard working week consists of 40 hours per team contributor",
                "Documents contain authentic business specifications without adversarial prompt injections",
            ],
            risks=risks,
            missing_information=missing_info,
            overall_confidence=0.92,
            uncertainty_notes=[
                "Commercial budget ceiling should be re-verified with Delivery Manager.",
            ],
        )
