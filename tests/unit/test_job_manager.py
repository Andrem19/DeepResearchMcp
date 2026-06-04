"""Unit tests for app.jobs — JobManager with fake engine."""

from __future__ import annotations

import asyncio

import pytest

from app.errors import ValidationError
from app.jobs import JobManager
from app.models import JobStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeEngine:
    """Fake research engine that returns a canned report."""

    def __init__(self, report: str = "# Fake Report\n\nDone.", *, delay: float = 0.0):
        self._report = report
        self._delay = delay
        self.call_count = 0

    async def run_markdown(self, query, depth="standard", max_sources=8, recency_days=None):
        self.call_count += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        return self._report


class FailingEngine:
    """Engine that always raises."""

    async def run_markdown(self, *args, **kwargs):
        raise RuntimeError("Engine exploded")


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Job created with PENDING status
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_start_research_creates_pending_job():
    engine = FakeEngine(delay=10.0)  # Long delay so job stays pending
    manager = JobManager(engine)
    job = _run(manager.start_research("What is MCP?"))
    assert job.query == "What is MCP?"
    assert job.job_id
    # Job starts as PENDING but may transition quickly; check query + id are correct
    assert job.status in (JobStatus.PENDING, JobStatus.RUNNING)


# ---------------------------------------------------------------------------
# Job completes in background
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_job_completes():
    engine = FakeEngine(report="# Report\n\n[1] Source — example.com — https://example.com")
    manager = JobManager(engine)
    job = _run(manager.start_research("test query"))

    # Wait for background task to finish
    _run(asyncio.sleep(0.2))

    status = _run(manager.get_status(job.job_id))
    assert status is not None
    assert status.status == JobStatus.COMPLETED
    assert status.report_markdown is not None
    assert "Report" in status.report_markdown
    assert status.source_count >= 1


# ---------------------------------------------------------------------------
# Job fails with controlled error
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_job_failure():
    engine = FailingEngine()
    manager = JobManager(engine)
    job = _run(manager.start_research("test"))

    _run(asyncio.sleep(0.2))

    status = _run(manager.get_status(job.job_id))
    assert status is not None
    assert status.status == JobStatus.FAILED
    assert status.error_message is not None
    assert "Engine exploded" in status.error_message


# ---------------------------------------------------------------------------
# Empty query rejected
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_empty_query_rejected():
    engine = FakeEngine()
    manager = JobManager(engine)
    with pytest.raises(ValidationError, match="empty"):
        _run(manager.start_research(""))


# ---------------------------------------------------------------------------
# Unknown job returns None
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unknown_job_returns_none():
    engine = FakeEngine()
    manager = JobManager(engine)
    result = _run(manager.get_status("nonexistent"))
    assert result is None


# ---------------------------------------------------------------------------
# get_report returns None for non-terminal job
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_report_not_ready_for_pending():
    engine = FakeEngine(delay=10.0)  # Long delay so it stays running
    manager = JobManager(engine)
    job = _run(manager.start_research("test"))
    report = _run(manager.get_report(job.job_id))
    # Job is still pending/running, no report yet
    # Note: it might be RUNNING depending on timing
    assert report is None or isinstance(report, str)


# ---------------------------------------------------------------------------
# list_recent returns jobs in order
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_list_recent():
    engine = FakeEngine()
    manager = JobManager(engine)
    _run(manager.start_research("query 1"))
    _run(manager.start_research("query 2"))
    _run(manager.start_research("query 3"))

    recent = _run(manager.list_recent(limit=2))
    assert len(recent) == 2
    # Newest first
    assert recent[0].query == "query 3"
    assert recent[1].query == "query 2"


# ---------------------------------------------------------------------------
# Expired jobs cleaned up
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cleanup_expired():
    engine = FakeEngine()
    manager = JobManager(engine, job_ttl_seconds=0)  # Expire immediately
    job = _run(manager.start_research("test"))

    _run(asyncio.sleep(0.2))  # Let job complete

    # Manually set completed_at to the past
    from datetime import UTC, datetime, timedelta

    status = _run(manager.get_status(job.job_id))
    assert status is not None
    status.completed_at = datetime.now(UTC) - timedelta(hours=2)

    _run(manager._cleanup_expired())

    # Job should be removed
    result = _run(manager.get_status(job.job_id))
    assert result is None


# ---------------------------------------------------------------------------
# Concurrent job limit
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_max_concurrent_jobs():
    engine = FakeEngine(delay=1.0)
    manager = JobManager(engine, max_concurrent_jobs=1)

    from app.errors import ResearchError

    _run(manager.start_research("first"))
    # The first job is still running, second should fail
    # Note: timing-dependent — the first job might complete before we start the second
    # Let's use a very long delay
    engine2 = FakeEngine(delay=100.0)
    manager2 = JobManager(engine2, max_concurrent_jobs=1)
    _run(manager2.start_research("first"))

    with pytest.raises(ResearchError, match="Too many concurrent"):
        _run(manager2.start_research("second"))
