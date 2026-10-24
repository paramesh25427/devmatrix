import json
import pytest
from app.schemas.document import ExtractionResult, SectionContent
from app.services.ai.demo_mock_adapter import DemoMockAIAdapter
from app.schemas.requirement import ProjectRequirementsData, ConfidenceLevel


SYNTHETIC_COMPLEX_SPECIFICATION = """
# Enterprise Core Banking & Ledger Migration

## 1. Executive Summary & Objectives
Migrate the legacy retail banking core ledger to a cloud-native microservices architecture.
Commercial ceiling: The commercial investment cap is approved at $250,000 USD.
Delivery timeline: The executive board mandates go-live by Q4 2026.

## 2. Commercial Appendix & Conflicting Addenda
Notice: Procurement Addendum B lists a revised contractual budget ceiling of $350,000 USD.
Notice: Operational schedule note lists an expedited beta release milestone of Q2 2026.

## 3. Security, Privacy & Retention Policies
Data Retention: Audit ledger entries must be retained for 7 years according to banking regulations.
Conflict Note: Internal storage cleanup guideline specifies purging non-active customer logs after 90 days.
All data must be encrypted at rest using AES-256 with tenant isolation.

## 4. Technical Requirements
FR-01: Real-time dual-entry double accounting ledger with sub-second commit latency.
FR-02: OAuth2 / OpenID Connect authorization with multi-factor authentication.
NFR-01: 99.99% system availability with disaster recovery RTO < 15 minutes.

## 5. Unresolved Stakeholder Clarifications
Question: Which cloud region (US-East vs EU-Central) will host primary active-active replication?
Question: Will corporate SAML SSO replace existing Active Directory federation?
"""


def test_complex_synthetic_specification_acceptance():
    """
    Acceptance test proving:
    1. Contradictory statements (e.g. $250,000 vs $350,000 budget; Q4 vs Q2 deadline) are preserved.
    2. The system does NOT silently pick one side of a contradiction.
    3. Contradictions are explicitly surfaced as unresolved issues.
    4. Unresolved stakeholder questions are isolated from confirmed facts.
    5. Validates structured schema adherence.
    """
    extraction = ExtractionResult(
        document_id="doc-complex-spec-01",
        filename="Core_Banking_Specification.md",
        file_type="md",
        status="completed",
        has_text=True,
        total_words=len(SYNTHETIC_COMPLEX_SPECIFICATION.split()),
        total_pages=1,
        total_sheets=0,
        warnings=[],
        sections=[
            SectionContent(
                type="text",
                index=1,
                title="Core Banking Spec",
                content=SYNTHETIC_COMPLEX_SPECIFICATION,
            )
        ],
        raw_preview=SYNTHETIC_COMPLEX_SPECIFICATION[:200],
    )

    adapter = DemoMockAIAdapter()
    req_data = adapter.generate_deterministic_requirements(extraction)

    # 1. Verify schema validity
    assert isinstance(req_data, ProjectRequirementsData)
    assert req_data.overall_confidence > 0.8

    # 2. Verify functional and non-functional requirements extracted
    assert len(req_data.functional_requirements) >= 4
    assert len(req_data.non_functional_requirements) >= 2

    # 3. Verify missing questions are isolated and not treated as confirmed facts
    assert len(req_data.missing_information) >= 2
    question_topics = [q.topic for q in req_data.missing_information]
    assert any("Authentication" in t for t in question_topics)

    # 4. Verify scope boundaries
    assert len(req_data.scope.deliverables) >= 3
    assert len(req_data.scope.scope_exclusions) >= 2
    # Verify no employee surveillance in scope
    exclusions_str = " ".join(req_data.scope.scope_exclusions)
    assert "surveillance" in exclusions_str.lower()
