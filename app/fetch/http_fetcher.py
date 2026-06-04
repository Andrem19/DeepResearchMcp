"""HTTP page fetcher using httpx with URL safety checks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx

from app.fetch.url_safety import validate_url
from app.models import FetchedPage

if TYPE_CHECKING:
    from app.config import AppConfig


class HttpFetcher:
    """Fetches web pages via HTTP with safety and size limits."""

    def __init__(
        self,
        config: AppConfig,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(config.fetch_timeout_seconds),
            follow_redirects=True,
            max_redirects=5,
            headers={"User-Agent": "DeepResearch-MCP/0.1"},
        )
        self._owns_client = client is None

    async def fetch(self, url: str) -> FetchedPage:
        """Fetch a single URL and return a FetchedPage.

        Validates URL safety before fetching.
        Checks final URL after redirects.
        """
        # Validate URL safety
        try:
            validate_url(
                url,
                allowed_domains=self._config.allowed_domains or None,
                blocked_domains=self._config.blocked_domains or None,
            )
        except Exception as exc:
            return FetchedPage(url=url, error=str(exc))

        try:
            response = await self._client.get(url)

            # Validate final URL after redirects
            final_url = str(response.url)
            try:
                validate_url(
                    final_url,
                    allowed_domains=self._config.allowed_domains or None,
                    blocked_domains=self._config.blocked_domains or None,
                )
            except Exception as exc:
                return FetchedPage(url=url, final_url=final_url, error=str(exc))

            # Check content type
            content_type = response.headers.get("content-type", "")
            if not _is_accepted_content_type(content_type):
                return FetchedPage(
                    url=url,
                    final_url=final_url,
                    status_code=response.status_code,
                    content_type=content_type,
                    error=f"Unsupported content type: {content_type}",
                )

            # Check size
            body = response.content
            if len(body) > self._config.max_fetch_bytes:
                body = body[: self._config.max_fetch_bytes]

            return FetchedPage(
                url=url,
                final_url=final_url,
                status_code=response.status_code,
                content_type=content_type,
                body=body,
                fetched_at=datetime.now(UTC),
            )

        except httpx.TimeoutException as exc:
            return FetchedPage(url=url, error=f"Timeout: {exc}")
        except httpx.HTTPError as exc:
            return FetchedPage(url=url, error=f"HTTP error: {exc}")

    async def fetch_many(self, urls: list[str], *, max_concurrency: int = 5) -> list[FetchedPage]:
        """Fetch multiple URLs with concurrency limit."""
        import asyncio

        semaphore = asyncio.Semaphore(max_concurrency)

        async def _fetch_with_semaphore(url: str) -> FetchedPage:
            async with semaphore:
                return await self.fetch(url)

        tasks = [_fetch_with_semaphore(url) for url in urls]
        return list(await asyncio.gather(*tasks))

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client:
            await self._client.aclose()


class FakeFetcher:
    """Fake fetcher for testing. Returns fixture HTML pages."""

    def __init__(
        self,
        pages: dict[str, bytes] | None = None,
        *,
        fail_urls: set[str] | None = None,
    ) -> None:
        self._pages = pages or _default_fake_pages()
        self._fail_urls = fail_urls or set()

    async def fetch(self, url: str) -> FetchedPage:
        if url in self._fail_urls:
            return FetchedPage(url=url, error=f"Simulated failure for {url}")

        if url in self._pages:
            return FetchedPage(
                url=url,
                final_url=url,
                status_code=200,
                content_type="text/html",
                body=self._pages[url],
                fetched_at=datetime.now(UTC),
            )

        return FetchedPage(url=url, status_code=404, error="Not found")

    async def fetch_many(self, urls: list[str], *, max_concurrency: int = 5) -> list[FetchedPage]:
        import asyncio

        tasks = [self.fetch(url) for url in urls]
        return list(await asyncio.gather(*tasks))

    async def close(self) -> None:
        pass


def _is_accepted_content_type(content_type: str) -> bool:
    """Check if content type is accepted for extraction."""
    ct_lower = content_type.lower()
    return any(
        ct_lower.startswith(accepted)
        for accepted in ("text/html", "text/plain", "application/xhtml")
    )


def _default_fake_pages() -> dict[str, bytes]:
    """Default HTML pages for fake fetcher."""
    return {
        "https://example.com/mcp-intro": b"""<!DOCTYPE html>
<html><head><title>Introduction to MCP Protocol</title></head>
<body>
<nav>Navigation</nav>
<main>
<h1>Introduction to MCP Protocol</h1>
<p>The Model Context Protocol (MCP) enables communication between AI models and external tools.
It provides a standardized way for models to access data and perform actions.</p>
<p>MCP uses a client-server architecture where the AI model acts as a client connecting to
MCP servers that provide tools and resources.</p>
</main>
<footer>Footer content</footer>
</body></html>""",
        "https://example.com/mcp-streamable-http": b"""<!DOCTYPE html>
<html><head><title>MCP Streamable HTTP Transport</title></head>
<body>
<main>
<h1>Streamable HTTP Transport</h1>
<p>The Streamable HTTP transport allows MCP servers to operate without maintaining
persistent connections. This makes deployment simpler behind load balancers and
reverse proxies.</p>
<p>Unlike the original SSE transport, Streamable HTTP supports both stateless and
stateful modes of operation.</p>
</main>
</body></html>""",
        "https://example.com/fastmcp-docs": b"""<!DOCTYPE html>
<html><head><title>FastMCP Documentation</title></head>
<body>
<main>
<h1>FastMCP Framework</h1>
<p>FastMCP is a Python framework for building MCP servers quickly and efficiently.
It provides decorators for defining tools, resources, and prompts.</p>
<p>FastMCP supports both stdio and HTTP transports, making it suitable for local
development and production deployment.</p>
</main>
</body></html>""",
    }
