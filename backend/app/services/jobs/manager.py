import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Coroutine
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.job import BackgroundJob

logger = logging.getLogger("devmatrix.jobs")


class JobManager:
    """
    Manages in-process asynchronous observable jobs with database persistence.
    Tracks state transitions: queued -> running -> succeeded / partially_succeeded / failed / cancelled.
    """

    _active_tasks: Dict[str, asyncio.Task] = {}

    @classmethod
    def create_job(
        cls,
        db: Session,
        tenant_id: str,
        job_type: str,
        project_id: Optional[str] = None,
        document_id: Optional[str] = None,
        message: str = "Job queued for processing",
    ) -> BackgroundJob:
        """Creates and persists a new queued background job."""
        # Prevent duplicate running jobs for same document and job_type
        if document_id:
            existing = (
                db.query(BackgroundJob)
                .filter(
                    BackgroundJob.document_id == document_id,
                    BackgroundJob.job_type == job_type,
                    BackgroundJob.status.in_(["queued", "running"]),
                )
                .first()
            )
            if existing:
                return existing

        job_id = str(uuid.uuid4())
        job = BackgroundJob(
            id=job_id,
            tenant_id=tenant_id,
            project_id=project_id,
            document_id=document_id,
            job_type=job_type,
            status="queued",
            progress_pct=5,
            message=message,
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def launch_job(
        cls,
        job_id: str,
        coroutine_func: Callable[..., Coroutine[Any, Any, Any]],
        *args,
        **kwargs,
    ) -> str:
        """Launches the background coroutine in the active event loop."""
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                cls._execute_wrapper(job_id, coroutine_func, *args, **kwargs)
            )
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
                task = asyncio.run_coroutine_threadsafe(
                    cls._execute_wrapper(job_id, coroutine_func, *args, **kwargs),
                    loop,
                )
            except Exception:
                task = asyncio.create_task(
                    cls._execute_wrapper(job_id, coroutine_func, *args, **kwargs)
                )
        cls._active_tasks[job_id] = task
        return job_id

    @classmethod
    async def _execute_wrapper(
        cls,
        job_id: str,
        coroutine_func: Callable[..., Coroutine[Any, Any, Any]],
        *args,
        **kwargs,
    ):
        """Wraps coroutine execution with database status updates and error handling."""
        db = SessionLocal()
        try:
            # Transition to running
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if not job:
                return
            job.status = "running"
            job.started_at = datetime.utcnow()
            job.progress_pct = 20
            job.message = "Job is actively running"
            db.commit()

            # Execute actual workload
            result = await coroutine_func(job_id, *args, **kwargs)

            # Mark succeeded
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if job and job.status != "cancelled":
                job.status = "succeeded"
                job.progress_pct = 100
                job.message = "Job completed successfully"
                job.completed_at = datetime.utcnow()
                if result:
                    job.result_json = (
                        json.dumps(result) if not isinstance(result, str) else result
                    )
                db.commit()
        except asyncio.CancelledError:
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if job:
                job.status = "cancelled"
                job.message = "Job was cancelled by user"
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception as exc:
            logger.exception(f"Background job {job_id} encountered an error: {exc}")
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.message = f"Job failed: {str(exc)}"
                job.error_json = json.dumps({"error": str(exc), "type": type(exc).__name__})
                job.completed_at = datetime.utcnow()
                db.commit()
        finally:
            cls._active_tasks.pop(job_id, None)
            db.close()

    @classmethod
    def update_progress(cls, job_id: str, progress_pct: int, message: str):
        """Updates progress percentage and status message."""
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if job and job.status == "running":
                job.progress_pct = min(max(progress_pct, 0), 99)
                job.message = message
                db.commit()
        finally:
            db.close()

    @classmethod
    def cancel_job(cls, job_id: str) -> bool:
        """Cancels an active running or queued job."""
        task = cls._active_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            return True
        db = SessionLocal()
        try:
            job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
            if job and job.status in ("queued", "running"):
                job.status = "cancelled"
                job.completed_at = datetime.utcnow()
                job.message = "Job cancelled by manager"
                db.commit()
                return True
            return False
        finally:
            db.close()
