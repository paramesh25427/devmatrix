import json
from typing import Dict, Any
from app.schemas.document import ExtractionResult

SYSTEM_INSTRUCTION = """You are DevMatrix AI, an advanced systems architect and workforce intelligence platform.
Your task is to analyze project intake documents and extract a comprehensive, structured project requirements specification.

MANDATORY RULES:
1. STRICT TRUTHFULNESS & PROVENANCE: Do not invent, hallucinate, or assume facts not present in the document. Every extracted requirement and risk MUST cite an exact source location (e.g. 'Page 1', 'Sheet: Milestones, Row 2', 'Section 1') matching the [SOURCE: ...] tags in the input.
2. STABLE IDENTIFIERS: Assign deterministic, stable IDs:
   - Functional Requirements: 'FR-01', 'FR-02', etc.
   - Non-Functional Requirements: 'NFR-01', 'NFR-02', etc.
   - Risks: 'RSK-01', 'RSK-02', etc.
   - Missing Information: 'Q-01', 'Q-02', etc.
3. CONFIDENCE & VERIFICATION:
   - 'confidence': Must be 'high' (explicit direct statement), 'medium' (synthesized across sections), or 'low' (inferred).
   - 'needs_verification': Set to true if a requirement is ambiguous, unquantified, conflicting, or lacks clear acceptance criteria. Provide a concise 'verification_reason'.
4. MISSING INFORMATION & CLARIFICATION:
   - Any missing detail (e.g., unspecified authentication mechanism, missing non-functional SLAs, target cloud environment) MUST be placed into 'missing_information' as clarification questions.
   - Missing information must NEVER be assumed or treated as confirmed facts.
5. SCOPE DISCIPLINE:
   - Distinguish explicit scope_inclusions from explicit scope_exclusions.
6. JSON COMPLIANCE:
   - Return ONLY a valid JSON object matching the required schema. Do not include introductory text or trailing conversational remarks.
"""

JSON_SCHEMA_GUIDE = {
    "project_summary": "Executive summary of the project intake",
    "objectives": ["Primary business or technical objectives"],
    "scope": {
        "deliverables": ["Tangible outputs expected"],
        "scope_inclusions": ["Features explicitly in scope"],
        "scope_exclusions": ["Features explicitly out of scope"],
    },
    "functional_requirements": [
        {
            "id": "FR-01",
            "title": "Short title",
            "description": "Detailed requirement specification",
            "category": "Domain category",
            "source_references": [
                {
                    "source_type": "page|sheet|table|section",
                    "location": "Page 1 or Sheet name",
                    "excerpt": "Quoted text",
                }
            ],
            "confidence": "high|medium|low",
            "needs_verification": False,
            "verification_reason": None,
        }
    ],
    "non_functional_requirements": [
        {
            "id": "NFR-01",
            "title": "Short title",
            "description": "Performance, security, or reliability criteria",
            "category": "Security|Performance|Availability",
            "source_references": [
                {
                    "source_type": "page|sheet|table|section",
                    "location": "Page 2",
                    "excerpt": "Quoted text",
                }
            ],
            "confidence": "high|medium|low",
            "needs_verification": False,
            "verification_reason": None,
        }
    ],
    "constraints": ["Technical, regulatory, or business constraints"],
    "dependencies": ["Prerequisite systems or integrations"],
    "assumptions": ["Assumptions identified in document"],
    "risks": [
        {
            "id": "RSK-01",
            "description": "Potential risk description",
            "severity": "high|medium|low",
            "mitigation_hint": "Optional mitigation",
            "source_reference": {
                "source_type": "page|sheet|table|section",
                "location": "Page 1",
                "excerpt": "Quoted text",
            },
        }
    ],
    "missing_information": [
        {
            "id": "Q-01",
            "topic": "Topic area",
            "question": "Clarification question for project stakeholders",
            "impact": "high|medium|low",
        }
    ],
    "overall_confidence": 0.85,
    "uncertainty_notes": ["Notes on ambiguous or unverified elements"],
}


def build_provenance_context(extraction: ExtractionResult) -> str:
    """Formats document sections into provenance-tagged text for AI ingestion."""
    lines = [
        f"DOCUMENT TITLE: {extraction.filename}",
        f"FILE TYPE: {extraction.file_type.upper()}",
        f"TOTAL PAGES: {extraction.total_pages}",
        f"TOTAL SHEETS: {extraction.total_sheets}",
        "",
        "--- DOCUMENT CONTENT WITH SOURCE PROVENANCE ---",
    ]

    for sec in extraction.sections:
        lines.append(f"\n[SOURCE: {sec.title}]")
        if sec.content:
            lines.append(sec.content.strip())
        if sec.table:
            headers = " | ".join(str(h) for h in sec.table.headers)
            lines.append(f"Headers: {headers}")
            for row in sec.table.rows:
                row_str = " | ".join(str(c) if c is not None else "" for c in row)
                lines.append(f"Row: {row_str}")

    return "\n".join(lines)


def build_user_prompt(extraction: ExtractionResult, repair_feedback: str = None) -> str:
    """Constructs the prompt for the AI provider with optional repair feedback."""
    context = build_provenance_context(extraction)
    prompt = (
        f"{context}\n\n"
        "--- INSTRUCTIONS ---\n"
        "Analyze the document above and extract the complete project requirements adhering to the rules.\n"
        f"Your response must be a JSON object adhering to this schema structure:\n"
        f"{json.dumps(JSON_SCHEMA_GUIDE, indent=2)}\n"
    )

    if repair_feedback:
        prompt += (
            "\n--- REPAIR REQUIRED ---\n"
            "Your previous output failed validation. Correct the following error and output valid JSON:\n"
            f"{repair_feedback}\n"
        )

    return prompt
