import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.requirement import RequirementDraft
from app.schemas.document import ExtractionResult
from app.services.ai.router import AIFallbackRouter
from app.services.jobs.manager import JobManager

logger = logging.getLogger("devmatrix.requirements.worker")


async def execute_async_extraction_job(job_id: str, document_id: str, tenant_id: str, project_id: str = None) -> Dict[str, Any]:
    """
    Background worker task for observable requirement extraction.
    Updates progress through the JobManager and persists the resulting draft.
    """
    db = SessionLocal()
    try:
        # Step 1: Verify document
        JobManager.update_progress(job_id, 25, "Verifying extracted document content")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found.")
        if not doc.has_text or (doc.total_words or 0) == 0:
            raise ValueError("Document has no extractable text content to process with AI.")

        # Step 2: Load extraction artifact
        JobManager.update_progress(job_id, 45, "Loading parsed document sections")
        extracted_json_path = os.path.join(settings.extracted_dir, f"{document_id}.json")
        if not os.path.exists(extracted_json_path):
            raise FileNotFoundError(f"Extracted content artifact for document '{document_id}' is missing.")

        with open(extracted_json_path, "r", encoding="utf-8") as f:
            extraction_dict = json.load(f)
            extraction = ExtractionResult.model_validate(extraction_dict)

        # Step 3: Run AI router fallback
        JobManager.update_progress(job_id, 65, "Executing multi-provider AI extraction pipeline")
        router = AIFallbackRouter()
        req_data, provider_used, model_used, attempt_history = await router.extract_requirements(extraction)

        # Step 4: Persist draft requirements payload
        JobManager.update_progress(job_id, 85, "Saving validated requirements payload")
        draft_id = str(uuid.uuid4())
        raw_json_path = os.path.join(settings.requirements_dir, f"{draft_id}.json")
        with open(raw_json_path, "w", encoding="utf-8") as f:
            json.dump(req_data.model_dump(), f, ensure_ascii=False, indent=2)

        # Step 5: Save draft record in database
        attempts_dicts = [a.model_dump() for a in attempt_history]
        draft_record = RequirementDraft(
            id=draft_id,
            tenant_id=tenant_id,
            project_id=project_id or doc.project_id or "proj-default",
            document_id=doc.id,
            document_name=doc.original_filename,
            provider_used=provider_used,
            model_used=model_used,
            status="draft_ready",
            review_status="pending_review",
            summary=req_data.project_summary if isinstance(req_data.project_summary, str) else getattr(req_data.project_summary, "summary", ""),
            overall_confidence=float(getattr(req_data, "overall_confidence", 0.85)),
            raw_json_path=raw_json_path,
            attempt_history_json=json.dumps(attempts_dicts),
            version=1,
            is_approved_baseline=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(draft_record)
        db.commit()

        return {
            "draft_id": draft_id,
            "document_id": document_id,
            "document_name": doc.original_filename,
            "provider_used": provider_used,
            "model_used": model_used,
            "summary": req_data.project_summary if isinstance(req_data.project_summary, str) else getattr(req_data.project_summary, "summary", ""),
            "total_functional": len(req_data.functional_requirements),
            "total_non_functional": len(req_data.non_functional_requirements),
            "total_conflicts": len(getattr(req_data, "contradictions", [])),
            "total_questions": len(req_data.missing_information),
        }
    finally:
        db.close()
