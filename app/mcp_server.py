"""MCP Server — thin adapter exposing deep_research tools via FastMCP.

This module contains NO business logic. It delegates everything to ResearchEngine.
"""

from __future__ import annotations

from fastmcp import FastMCP

from app.observability.logging import setup_logging

# Initialize MCP server
mcp = FastMCP("DeepResearch")

# Module-level engine and job manager (initialized lazily)
_engine = None
_job_manager = None


def _get_engine():
    """Lazy-init the research engine."""
    global _engine
    if _engine is None:
        from app.config import load_config
        from app.research_engine import create_engine
        config = load_config()
        setup_logging(config.log_level)
        _engine = create_engine(config)
    return _engine


def _get_job_manager():
    """Lazy-init the job manager."""
    global _job_manager
    if _job_manager is None:
        from app.jobs import JobManager
        _job_manager = JobManager(_get_engine())
    return _job_manager


@mcp.tool()
async def deep_research(
    query: str,
    depth: str = "standard",
    max_sources: int = 8,
    recency_days: int | None = None,
    output_format: str = "markdown",
) -> str:
    """Deep research tool — searches, reads, compares sources, and returns a Markdown report with citations.

    This tool independently performs web search, reads multiple sources,
    extracts key information, cross-references evidence, and generates
    a comprehensive research report. The result may contain limitations
    if sources are scarce or conflicting.

    Args:
        query: Research question or topic to investigate.
        depth: Research depth — "quick" (2 queries), "standard" (4 queries), "deep" (6 queries).
        max_sources: Maximum number of sources to include (server enforces upper limit).
        recency_days: Only include sources from the last N days. None = no filter.
        output_format: Output format. Currently only "markdown" is supported.

    Returns:
        Markdown research report with summary, key findings, sources, and limitations.
    """
    engine = _get_engine()
    return await engine.run_markdown(query, depth, max_sources, recency_days)


# ---------------------------------------------------------------------------
# Async job tools (Stage 26 — for long-running research)
# ---------------------------------------------------------------------------


@mcp.tool()
async def start_deep_research(
    query: str,
    depth: str = "standard",
    max_sources: int = 8,
    recency_days: int | None = None,
) -> str:
    """Start a background research job. Returns a job_id immediately.

    Use get_research_status to check progress and get_research_report to retrieve results.
    This is useful for long-running research that may exceed client timeouts.

    Args:
        query: Research question or topic to investigate.
        depth: Research depth — "quick", "standard", or "deep".
        max_sources: Maximum number of sources to include.
        recency_days: Only include sources from the last N days. None = no filter.

    Returns:
        JSON with job_id and status.
    """
    import json

    manager = _get_job_manager()
    job = await manager.start_research(query, depth, max_sources, recency_days)
    return json.dumps({
        "job_id": job.job_id,
        "status": job.status.value,
        "query": job.query,
        "depth": job.depth,
        "created_at": job.created_at.isoformat(),
    })


@mcp.tool()
async def get_research_status(job_id: str) -> str:
    """Check the status of a background research job.

    Args:
        job_id: The job identifier returned by start_deep_research.

    Returns:
        JSON with job status, progress info, and error details if failed.
    """
    import json

    manager = _get_job_manager()
    job = await manager.get_status(job_id)
    if job is None:
        return json.dumps({"error": f"Job {job_id!r} not found"})

    result = {
        "job_id": job.job_id,
        "status": job.status.value,
        "query": job.query,
        "source_count": job.source_count,
        "duration_seconds": job.research_duration_seconds,
    }

    if job.error_message:
        result["error"] = job.error_message

    if job.completed_at:
        result["completed_at"] = job.completed_at.isoformat()

    return json.dumps(result)


@mcp.tool()
async def get_research_report(job_id: str) -> str:
    """Get the Markdown report for a completed research job.

    Only returns results when the job status is "completed" or "failed".

    Args:
        job_id: The job identifier returned by start_deep_research.

    Returns:
        Markdown research report, or an error message if not ready.
    """
    manager = _get_job_manager()
    job = await manager.get_status(job_id)
    if job is None:
        return f"Error: Job {job_id!r} not found."
    if job.status.value == "pending":
        return "Job is still queued. Please check again later."
    if job.status.value == "running":
        return "Job is still in progress. Please check again later."
    if job.status.value == "expired":
        return "Job has expired. Please start a new research job."
    if job.status.value == "failed":
        return f"Research failed: {job.error_message or 'Unknown error'}"
    return job.report_markdown or "Error: No report available."


@mcp.tool()
async def list_recent_research(limit: int = 10) -> str:
    """List recent research jobs (newest first).

    Args:
        limit: Maximum number of jobs to return (default 10, max 50).

    Returns:
        JSON array of recent jobs with status info.
    """
    import json

    limit = max(1, min(limit, 50))
    manager = _get_job_manager()
    jobs = await manager.list_recent(limit)
    return json.dumps([
        {
            "job_id": j.job_id,
            "query": j.query,
            "status": j.status.value,
            "source_count": j.source_count,
            "created_at": j.created_at.isoformat(),
        }
        for j in jobs
    ])


def main() -> None:
    """Run the MCP server."""
    from app.config import load_config

    config = load_config()
    setup_logging(config.log_level)

    # Pre-initialize engine
    global _engine
    from app.research_engine import create_engine
    _engine = create_engine(config)

    if config.mcp_transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="streamable-http",
            host=config.host,
            port=config.port,
            path=config.mcp_path,
        )


if __name__ == "__main__":
    main()
