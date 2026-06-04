"""Job Manager — async research jobs with background execution (Stage 26).

Manages the lifecycle of background research jobs:
  PENDING -> RUNNING -> COMPLETED/FAILED
Jobs can expire after a configurable TTL.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.errors import ResearchError, ValidationError
from app.models import JobStatus, ResearchJob

if TYPE_CHECKING:
    from app.research_engine import ResearchEngine


class JobManager:
    """Manages async research jobs with in-memory storage.

    For MVP, jobs are stored in-memory. A persistent backend
    can be added later via the storage layer.
    """

    def __init__(
        self,
        engine: ResearchEngine,
        *,
        max_concurrent_jobs: int = 5,
        job_ttl_seconds: int = 3600,
        cleanup_interval_seconds: int = 300,
    ) -> None:
        self._engine = engine
        self._jobs: dict[str, ResearchJob] = {}
        self._max_concurrent_jobs = max_concurrent_jobs
        self._job_ttl_seconds = job_ttl_seconds
        self._cleanup_interval_seconds = cleanup_interval_seconds
        self._running_count = 0
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task
            self._cleanup_task = None

    async def start_research(
        self,
        query: str,
        depth: str = "standard",
        max_sources: int = 8,
        recency_days: int | None = None,
    ) -> ResearchJob:
        """Create and start a new research job.

        Returns immediately with a PENDING job.
        The actual research runs in the background.
        """
        # Validate
        if not query or not query.strip():
            raise ValidationError("Query must not be empty")

        if self._running_count >= self._max_concurrent_jobs:
            raise ResearchError(
                f"Too many concurrent jobs (max {self._max_concurrent_jobs}). "
                "Please try again later."
            )

        job = ResearchJob(
            job_id=uuid.uuid4().hex[:12],
            query=query.strip(),
            depth=depth,
            max_sources=max_sources,
            recency_days=recency_days,
        )

        self._jobs[job.job_id] = job

        # Start background execution
        asyncio.create_task(self._run_job(job.job_id))

        return job

    async def get_status(self, job_id: str) -> ResearchJob | None:
        """Get the current status of a job."""
        return self._jobs.get(job_id)

    async def get_report(self, job_id: str) -> str | None:
        """Get the report for a completed job."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if not job.is_terminal:
            return None
        return job.report_markdown

    async def list_recent(self, limit: int = 10) -> list[ResearchJob]:
        """List recent jobs, ordered by creation time (newest first)."""
        jobs = sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )
        return jobs[:limit]

    async def _run_job(self, job_id: str) -> None:
        """Execute a research job in the background."""
        job = self._jobs.get(job_id)
        if job is None:
            return

        async with self._lock:
            self._running_count += 1

        try:
            # Update status to RUNNING
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)

            # Run the actual research
            report_md = await self._engine.run_markdown(
                query=job.query,
                depth=job.depth,
                max_sources=job.max_sources,
                recency_days=job.recency_days,
            )

            # Extract source count from report if possible
            source_count = self._count_sources(report_md)

            # Update job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.report_markdown = report_md
            job.source_count = source_count
            if job.started_at:
                job.research_duration_seconds = (
                    datetime.now(UTC) - job.started_at
                ).total_seconds()

        except Exception as exc:
            # Update job as failed
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(UTC)
            job.error_message = str(exc)[:500]

        finally:
            async with self._lock:
                self._running_count -= 1

    def _count_sources(self, report_md: str) -> int:
        """Try to count sources from the report markdown."""
        # Look for lines like [1] Title — domain — URL
        count = 0
        for line in report_md.split("\n"):
            stripped = line.strip()
            if stripped.startswith("[") and "]" in stripped and "http" in stripped:
                count += 1
        return count

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired jobs."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval_seconds)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception:
                # Don't let cleanup errors crash the loop
                pass

    async def _cleanup_expired(self) -> None:
        """Remove jobs that have exceeded their TTL."""
        now = datetime.now(UTC)
        expired_ids: list[str] = []

        for job_id, job in self._jobs.items():
            if job.is_terminal and job.completed_at:
                age = (now - job.completed_at).total_seconds()
                if age > self._job_ttl_seconds:
                    expired_ids.append(job_id)

        for job_id in expired_ids:
            job = self._jobs.pop(job_id, None)
            if job:
                job.status = JobStatus.EXPIRED
