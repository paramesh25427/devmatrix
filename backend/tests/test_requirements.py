import json
import logging
import os
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.document import Document
from app.models.requirement import RequirementDraft
from app.schemas.requirement import ProjectRequirementsData
from app.services.ai.exceptions import (
    AuthenticationError,
    RateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    InvalidResponseError,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def set_auth_header():
    """Authenticates client as delivery manager to preserve authorized test workflows."""
    from app.core.security import create_access_token
    token = create_access_token(
        user_id="user-mgr-a",
        email="manager@devmatrix.local",
        role="delivery_manager",
        tenant_id="tenant-default",
    )
    client.headers["Authorization"] = f"Bearer {token}"

SAMPLE_VALID_REQUIREMENTS = {
    "project_summary": "DevMatrix AI is an automated project intake and workforce intelligence platform.",
    "objectives": [
        "Automate requirement extraction from multi-format intake documents",
        "Provide unified sprint planning with skill-based resource matching",
    ],
    "scope": {
        "deliverables": ["Intake service", "Multi-provider AI router", "Review dashboard"],
        "scope_inclusions": ["PDF/DOCX/XLSX parsing", "Gemini, Grok, and NVIDIA NIM adapters"],
        "scope_exclusions": ["Autonomous managerial approvals", "OpenAI integration"],
    },
    "functional_requirements": [
        {
            "id": "FR-01",
            "title": "Document Content Extraction",
            "description": "System shall extract text and tables from uploaded PDF, DOCX, XLSX, and CSV documents.",
            "category": "Core Intake",
            "source_references": [
                {
                    "source_type": "page",
                    "location": "Page 1",
                    "excerpt": "Extract text and tables preserving ordering",
                }
            ],
            "confidence": "high",
            "needs_verification": False,
            "verification_reason": None,
        },
        {
            "id": "FR-02",
            "title": "Fallback AI Routing",
            "description": "System shall route extraction through Gemini, Grok, and NVIDIA NIM in priority order.",
            "category": "AI Pipeline",
            "source_references": [
                {
                    "source_type": "section",
                    "location": "Section 2",
                    "excerpt": "Sequential fallback across providers",
                }
            ],
            "confidence": "medium",
            "needs_verification": True,
            "verification_reason": "Specific fallback timeout limits need confirmation",
        },
    ],
    "non_functional_requirements": [
        {
            "id": "NFR-01",
            "title": "Bounded Memory Consumption",
            "description": "Upload processing must stream in chunks of 1 MiB to prevent memory exhaustion.",
            "category": "Performance",
            "source_references": [
                {
                    "source_type": "section",
                    "location": "Section 3",
                    "excerpt": "Chunked upload streaming",
                }
            ],
            "confidence": "high",
            "needs_verification": False,
            "verification_reason": None,
        }
    ],
    "constraints": ["Must execute on Python 3.11 with SQLite"],
    "dependencies": ["Google Gemini API", "xAI Grok API", "NVIDIA NIM"],
    "assumptions": ["Documents will be provided in English"],
    "risks": [
        {
            "id": "RSK-01",
            "description": "External AI provider API quotas may cause transient rate limits.",
            "severity": "medium",
            "mitigation_hint": "Automated exponential backoff and ordered provider fallback.",
            "source_reference": {
                "source_type": "section",
                "location": "Section 2",
                "excerpt": "Transient rate limits",
            },
        }
    ],
    "missing_information": [
        {
            "id": "Q-01",
            "topic": "Storage Quota",
            "question": "What is the maximum retention period for raw project documents?",
            "impact": "low",
        }
    ],
    "overall_confidence": 0.90,
    "uncertainty_notes": ["Verify retention SLA with infrastructure team"],
}


@pytest.fixture
def test_document_id():
    """Uploads a valid synthetic document and returns its ID."""
    content = b"DevMatrix AI Project Charter\nObjectives: Multi-provider AI requirement extraction and planning."
    res = client.post(
        "/api/documents/upload",
        files={"file": ("project_spec.txt", content, "text/plain")},
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]
    yield doc_id
    # Cleanup document after test
    client.delete(f"/api/documents/{doc_id}")


@pytest.fixture
def empty_text_document_id():
    """Uploads a synthetic blank PDF with no extractable text."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    import io
    buf = io.BytesIO()
    writer.write(buf)
    res = client.post(
        "/api/documents/upload",
        files={"file": ("blank_scan.pdf", buf.getvalue(), "application/pdf")},
    )
    assert res.status_code == 201
    doc_id = res.json()["id"]
    yield doc_id
    client.delete(f"/api/documents/{doc_id}")


def test_primary_provider_gemini_success(test_document_id):
    """Verify primary provider (Gemini) extracts and validates requirements."""
    mock_json = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = f"```json\n{mock_json}\n```"

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201
        data = res.json()

        assert data["provider_used"] == "gemini"
        assert data["model_used"] == settings.gemini_model
        assert data["status"] == "draft_ready"
        assert data["review_status"] == "pending_review"
        assert data["requirements"]["project_summary"].startswith("DevMatrix AI")
        assert len(data["requirements"]["functional_requirements"]) == 2
        assert data["requirements"]["functional_requirements"][0]["id"] == "FR-01"
        assert data["requirements"]["overall_confidence"] == 0.90
        assert len(data["attempt_history"]) == 1
        assert data["attempt_history"][0]["status"] == "success"


def test_default_router_provider_priority_excludes_grok():
    """Verify default router adapter order is strictly [Gemini, NVIDIA NIM] with Grok excluded."""
    from app.services.ai.router import AIFallbackRouter
    router = AIFallbackRouter()
    provider_names = [a.provider_name for a in router.adapters]
    assert provider_names == ["gemini", "nvidia_nim"]
    assert "grok" not in provider_names


def test_primary_rate_limit_fallback_to_nvidia(test_document_id):
    """Verify rate limit on primary (Gemini) triggers backoff and falls back to NVIDIA NIM, excluding Grok."""
    mock_json = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.is_configured", True), \
         patch("app.services.ai.grok_adapter.GrokAdapter.generate_json_text", new_callable=AsyncMock) as mock_grok, \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.generate_json_text", new_callable=AsyncMock) as mock_nvidia:

        # Gemini fails with 429 RateLimitError
        mock_gemini.side_effect = RateLimitError("Rate limit exceeded", "gemini", 429)
        # NVIDIA succeeds
        mock_nvidia.return_value = mock_json

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201
        data = res.json()

        assert data["provider_used"] == "nvidia_nim"
        assert data["status"] == "draft_ready"
        assert any(a["provider"] == "gemini" and a["status"] == "rate_limited" for a in data["attempt_history"])
        assert any(a["provider"] == "nvidia_nim" and a["status"] == "success" for a in data["attempt_history"])
        mock_grok.assert_not_called()


def test_gemini_503_fallback_to_nvidia(test_document_id):
    """Verify Gemini HTTP 503 retries, exhausts retries, and falls back to NVIDIA NIM; Grok is not called."""
    mock_json = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.is_configured", True), \
         patch("app.services.ai.grok_adapter.GrokAdapter.generate_json_text", new_callable=AsyncMock) as mock_grok, \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.generate_json_text", new_callable=AsyncMock) as mock_nvidia:

        # Gemini fails with transient 503 (service unavailable / high demand)
        mock_gemini.side_effect = ProviderUnavailableError(
            "This model is currently experiencing high demand. (503)",
            "gemini",
            503,
        )
        # NVIDIA succeeds
        mock_nvidia.return_value = mock_json

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201
        data = res.json()

        # NVIDIA NIM was invoked and succeeded
        assert data["provider_used"] == "nvidia_nim"
        assert data["status"] == "draft_ready"
        assert data["requirements"]["project_summary"].startswith("DevMatrix AI")
        assert len(data["requirements"]["functional_requirements"]) == 2

        # Telemetry verification: Gemini failed with server_error, NVIDIA succeeded
        assert len(data["attempt_history"]) == 2
        gemini_attempt = data["attempt_history"][0]
        assert gemini_attempt["provider"] == "gemini"
        assert gemini_attempt["status"] == "server_error"
        assert gemini_attempt["error_category"] == "server_error"
        assert gemini_attempt["attempt_count"] == settings.gemini_max_retries + 1

        nvidia_attempt = data["attempt_history"][1]
        assert nvidia_attempt["provider"] == "nvidia_nim"
        assert nvidia_attempt["status"] == "success"
        assert nvidia_attempt["error_category"] is None

        # Grok was never called by the default router
        mock_grok.assert_not_called()

        # Verify no secrets in telemetry
        telemetry_str = json.dumps(data["attempt_history"])
        assert "api_key" not in telemetry_str.lower()
        assert "x-goog-api-key" not in telemetry_str.lower()
        assert "bearer" not in telemetry_str.lower()
        assert "secret" not in telemetry_str.lower()


def test_both_providers_fail_preserves_document(test_document_id):
    """Verify that when both Gemini and NVIDIA fail transiently (503s), HTTP 502 is returned and document is preserved."""
    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.is_configured", True), \
         patch("app.services.ai.grok_adapter.GrokAdapter.generate_json_text", new_callable=AsyncMock) as mock_grok, \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.generate_json_text", new_callable=AsyncMock) as mock_nvidia:

        mock_gemini.side_effect = ProviderUnavailableError("Gemini 503 service unavailable", "gemini", 503)
        mock_nvidia.side_effect = ProviderUnavailableError("NVIDIA 503 service unavailable", "nvidia_nim", 503)

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 502
        error_detail = res.json()["detail"]
        assert "All configured AI providers in fallback sequence failed" in error_detail["message"]
        assert error_detail["document_preserved"] is True
        assert len(error_detail["attempts"]) == 2
        assert error_detail["attempts"][0]["provider"] == "gemini"
        assert error_detail["attempts"][1]["provider"] == "nvidia_nim"
        assert all(a["status"] == "server_error" for a in error_detail["attempts"])

        # Grok was never called
        mock_grok.assert_not_called()

        # Confirm document is still in database and accessible
        doc_res = client.get(f"/api/documents/{test_document_id}")
        assert doc_res.status_code == 200
        assert doc_res.json()["original_filename"] == "project_spec.txt"

        # Confirm error response contains no secrets
        raw_detail = json.dumps(error_detail)
        assert "api_key" not in raw_detail.lower()
        assert "secret" not in raw_detail.lower()


def test_permanent_auth_error_aborts_retries(test_document_id):
    """Verify permanent 401 AuthenticationError does not retry endlessly, switching immediately to NVIDIA NIM."""
    mock_json = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.is_configured", True), \
         patch("app.services.ai.grok_adapter.GrokAdapter.generate_json_text", new_callable=AsyncMock) as mock_grok, \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.generate_json_text", new_callable=AsyncMock) as mock_nvidia:

        # Gemini fails with permanent 401
        mock_gemini.side_effect = AuthenticationError("Invalid API key", "gemini", 401)
        mock_nvidia.return_value = mock_json

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201
        data = res.json()

        assert data["provider_used"] == "nvidia_nim"
        # Verify Gemini only attempted once (no retries on 401)
        gemini_attempt = [a for a in data["attempt_history"] if a["provider"] == "gemini"][0]
        assert gemini_attempt["attempt_count"] == 1
        assert gemini_attempt["status"] == "auth_error"
        mock_grok.assert_not_called()


def test_schema_validation_and_repair(test_document_id):
    """Verify invalid initial JSON triggers a repair attempt before succeeding."""
    broken_output = '{"project_summary": "Missing all other fields"}'
    repaired_output = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini:

        # First attempt returns broken schema, second attempt returns valid
        mock_gemini.side_effect = [broken_output, repaired_output]

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201
        data = res.json()

        assert data["provider_used"] == "gemini"
        assert data["attempt_history"][0]["status"] == "success"
        assert data["attempt_history"][0]["error_category"] == "repaired"


def test_no_text_document_rejected(empty_text_document_id):
    """Verify document with no extractable text is rejected with HTTP 400."""
    res = client.post(f"/api/requirements/extract/{empty_text_document_id}")
    assert res.status_code == 400
    assert "no extractable text content" in res.json()["detail"]


def test_missing_document_returns_404():
    """Verify non-existent document ID returns HTTP 404."""
    res = client.post("/api/requirements/extract/non-existent-uuid-999")
    assert res.status_code == 404


def test_manager_review_lifecycle(test_document_id):
    """Verify manager can review, approve, and record notes on an extracted draft."""
    mock_json = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_json

        extract_res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert extract_res.status_code == 201
        draft_id = extract_res.json()["id"]

        # 1. Fetch draft by ID
        get_res = client.get(f"/api/requirements/{draft_id}")
        assert get_res.status_code == 200
        assert get_res.json()["review_status"] == "pending_review"

        # 2. Fetch drafts by document ID
        doc_drafts = client.get(f"/api/requirements/document/{test_document_id}")
        assert doc_drafts.status_code == 200
        assert len(doc_drafts.json()) >= 1

        # 3. Manager approves draft with feedback
        review_payload = {
            "review_status": "approved",
            "manager_notes": "Approved for Sprint 1 architecture alignment.",
        }
        review_res = client.patch(f"/api/requirements/{draft_id}/review", json=review_payload)
        assert review_res.status_code == 200
        assert review_res.json()["review_status"] == "approved"
        assert review_res.json()["manager_notes"] == "Approved for Sprint 1 architecture alignment."


def test_no_secrets_or_document_content_in_telemetry(test_document_id, caplog):
    """Verify telemetry logs contain no API keys or full document bodies."""
    mock_json = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    with caplog.at_level(logging.INFO), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = mock_json

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201

        # Verify no placeholder or raw secrets in logs
        log_text = caplog.text
        assert "placeholder" not in log_text.lower()
        assert "x-goog-api-key" not in log_text
        assert "bearer" not in log_text.lower()


def test_configuration_and_timeout_propagation():
    """Verify backend settings load 60s Gemini, 120s NVIDIA timeout, 4096 max tokens, and 2.0s initial backoff."""
    from app.services.ai.gemini_adapter import GeminiAdapter
    from app.services.ai.nvidia_adapter import NvidiaNimAdapter

    assert settings.gemini_timeout_seconds == 60.0
    assert settings.gemini_max_retries == 1
    assert settings.nvidia_nim_timeout_seconds == 120.0
    assert settings.nvidia_nim_max_retries == 1
    assert settings.nvidia_nim_max_tokens == 4096
    assert settings.initial_retry_delay_seconds == 2.0
    assert settings.gemini_enabled is True
    assert settings.nvidia_nim_enabled is True
    assert settings.grok_enabled is False

    gemini = GeminiAdapter()
    assert gemini._timeout == 60.0
    custom_gemini = GeminiAdapter(timeout=45.0)
    assert custom_gemini._timeout == 45.0

    nvidia = NvidiaNimAdapter()
    assert nvidia._timeout == 120.0
    assert nvidia._max_tokens == 4096
    custom_nvidia = NvidiaNimAdapter(timeout=90.0, max_tokens=2048)
    assert custom_nvidia._timeout == 90.0
    assert custom_nvidia._max_tokens == 2048


def test_exhausted_provider_retries_and_timeout_error_telemetry(test_document_id):
    """Verify router retries each provider exactly once (2 attempts) on timeout, producing sanitized attempt history."""
    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.is_configured", True), \
         patch("app.services.ai.grok_adapter.GrokAdapter.generate_json_text", new_callable=AsyncMock) as mock_grok, \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.generate_json_text", new_callable=AsyncMock) as mock_nvidia, \
         patch("asyncio.sleep", new_callable=AsyncMock):

        mock_gemini.side_effect = ProviderTimeoutError("Gemini timed out after 60.0s", "gemini")
        mock_nvidia.side_effect = ProviderTimeoutError("NVIDIA NIM timed out after 120.0s", "nvidia_nim")

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 502
        error_detail = res.json()["detail"]

        assert "All configured AI providers in fallback sequence failed" in error_detail["message"]
        assert error_detail["document_preserved"] is True
        assert len(error_detail["attempts"]) == 2

        gemini_attempt = error_detail["attempts"][0]
        assert gemini_attempt["provider"] == "gemini"
        assert gemini_attempt["status"] == "timeout"
        assert gemini_attempt["error_category"] == "timeout"
        assert gemini_attempt["attempt_count"] == settings.gemini_max_retries + 1  # Exactly 2 attempts

        nvidia_attempt = error_detail["attempts"][1]
        assert nvidia_attempt["provider"] == "nvidia_nim"
        assert nvidia_attempt["status"] == "timeout"
        assert nvidia_attempt["error_category"] == "timeout"
        assert nvidia_attempt["attempt_count"] == settings.nvidia_nim_max_retries + 1  # Exactly 2 attempts

        mock_grok.assert_not_called()

        # Confirm zero secrets leaked in error detail
        raw_detail = json.dumps(error_detail)
        assert "api_key" not in raw_detail.lower()
        assert "secret" not in raw_detail.lower()


def test_configurable_backoff_and_retry_after(test_document_id):
    """Verify router uses provider Retry-After delay when present, and initial_retry_delay_seconds otherwise."""
    mock_json = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    # 1. When Retry-After is supplied by provider (e.g. 3.5s)
    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        mock_gemini.side_effect = [
            RateLimitError("Rate limit exceeded", "gemini", 429, retry_after=3.5),
            mock_json,
        ]

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201
        assert res.json()["provider_used"] == "gemini"
        mock_sleep.assert_called_once_with(3.5)

    # 2. When Retry-After is NOT supplied, uses configured initial delay (2.0s)
    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        mock_gemini.side_effect = [
            RateLimitError("Rate limit exceeded", "gemini", 429),
            mock_json,
        ]

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201
        assert res.json()["provider_used"] == "gemini"
        mock_sleep.assert_called_once_with(settings.initial_retry_delay_seconds)


def test_permanent_quota_exhaustion_aborts_retries_and_falls_back(test_document_id):
    """Verify permanent quota exhaustion (e.g. daily quota reached) aborts retries immediately and falls back to NVIDIA."""
    mock_json = json.dumps(SAMPLE_VALID_REQUIREMENTS)

    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.is_configured", True), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.generate_json_text", new_callable=AsyncMock) as mock_nvidia, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        # Gemini fails with permanent quota condition (requests per day exhausted)
        mock_gemini.side_effect = RateLimitError(
            "Resource has been exhausted: Quota exceeded for quota metric and limit 'Requests per day'",
            "gemini",
            429,
        )
        mock_nvidia.return_value = mock_json

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 201
        data = res.json()

        assert data["provider_used"] == "nvidia_nim"
        # Gemini was NOT retried (sleep was never called for retry)
        mock_sleep.assert_not_called()
        assert mock_gemini.call_count == 1

        gemini_attempt = [a for a in data["attempt_history"] if a["provider"] == "gemini"][0]
        assert gemini_attempt["status"] == "rate_limited"
        assert gemini_attempt["error_category"] == "quota_exhausted"


def test_nvidia_nim_truncation_detection(test_document_id):
    """Verify truncated output with finish_reason='length' is detected and rejected, never saved as draft."""
    with patch("app.services.ai.gemini_adapter.GeminiAdapter.is_configured", True), \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.is_configured", True), \
         patch("app.services.ai.gemini_adapter.GeminiAdapter.generate_json_text", new_callable=AsyncMock) as mock_gemini, \
         patch("app.services.ai.nvidia_adapter.NvidiaNimAdapter.generate_json_text", new_callable=AsyncMock) as mock_nvidia:

        mock_gemini.side_effect = ProviderUnavailableError("Gemini 503 unavailable", "gemini", 503)
        mock_nvidia.side_effect = InvalidResponseError(
            "NVIDIA NIM response truncated due to token limit (finish_reason='length').",
            "nvidia_nim",
            200,
        )

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 502
        error_detail = res.json()["detail"]

        assert error_detail["document_preserved"] is True
        nvidia_attempt = [a for a in error_detail["attempts"] if a["provider"] == "nvidia_nim"][0]
        assert nvidia_attempt["status"] == "invalid_response"
        assert nvidia_attempt["error_category"] == "truncated_or_invalid"

        # Verify no draft was saved
        drafts_res = client.get(f"/api/requirements/document/{test_document_id}")
        assert drafts_res.status_code == 200
        assert len(drafts_res.json()) == 0


@pytest.mark.asyncio
async def test_nvidia_nim_max_tokens_payload_passed():
    """Verify NvidiaNimAdapter passes configured max_tokens in chat completions payload."""
    from app.services.ai.nvidia_adapter import NvidiaNimAdapter
    import httpx

    adapter = NvidiaNimAdapter(api_key="test-key", max_tokens=3072)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {}
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {"content": '{"test": true}'},
                "finish_reason": "stop",
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        await adapter.generate_json_text("sys_inst", "user_prompt")

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        payload = kwargs.get("json", {})
        assert payload.get("max_tokens") == 3072


def test_missing_extracted_artifact_error_message(test_document_id):
    """Verify missing extraction artifact returns HTTP 404 with re-upload guidance and preserves document in DB."""
    # Temporarily remove disk artifact
    extracted_path = os.path.join(settings.extracted_dir, f"{test_document_id}.json")
    assert os.path.exists(extracted_path)
    with open(extracted_path, "r", encoding="utf-8") as f:
        saved_content = f.read()

    try:
        os.remove(extracted_path)

        res = client.post(f"/api/requirements/extract/{test_document_id}")
        assert res.status_code == 404
        assert res.json()["detail"] == f"The extracted content artifact for document '{test_document_id}' is missing. Please re-upload or re-process the document."

        # Verify document still exists in SQLite
        doc_res = client.get(f"/api/documents/{test_document_id}")
        assert doc_res.status_code == 200
        assert doc_res.json()["original_filename"] == "project_spec.txt"

    finally:
        # Restore artifact for fixture cleanup
        with open(extracted_path, "w", encoding="utf-8") as f:
            f.write(saved_content)


