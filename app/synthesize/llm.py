"""OpenAI-compatible LLM adapter for synthesis (optional, post-MVP).

Falls back to ExtractiveSynthesizer on failure.
Supports LM Studio local API as OpenAI-compatible endpoint.
"""

from __future__ import annotations

import asyncio
import re

import httpx

from app.errors import SynthesisError
from app.models import RankedSource, ResearchFinding
from app.synthesize.base import Synthesizer
from app.synthesize.extractive import ExtractiveSynthesizer
from app.synthesize.prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Transient HTTP status codes worth retrying
_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 1.0


class LLMSynthesizer(Synthesizer):
    """LLM-based synthesizer using OpenAI-compatible API.

    Falls back to ExtractiveSynthesizer on failure.
    Supports LM Studio local API via configurable api_base.
    """

    def __init__(
        self,
        api_key: str,
        *,
        api_base: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: float = 30.0,
        max_input_chars: int = 50_000,
        max_output_chars: int = 5000,
        max_retries: int = _MAX_RETRIES,
    ) -> None:
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_input_chars = max_input_chars
        self._max_output_chars = max_output_chars
        self._max_retries = max_retries
        self._fallback = ExtractiveSynthesizer()
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Authorization": f"Bearer {api_key}"},
        )

    @property
    def name(self) -> str:
        return f"llm:{self._model}"

    async def synthesize(
        self,
        query: str,
        sources: list[RankedSource],
    ) -> list[ResearchFinding]:
        """Synthesize findings using LLM, falling back to extractive on failure."""
        if not sources:
            return []

        try:
            return await self._llm_synthesize(query, sources)
        except Exception:
            # Fallback to extractive on any LLM failure
            return await self._fallback.synthesize(query, sources)

    async def _llm_synthesize(
        self,
        query: str,
        sources: list[RankedSource],
    ) -> list[ResearchFinding]:
        """Call LLM API with retry for transient errors."""
        evidence = self._build_evidence(sources)
        user_prompt = USER_PROMPT_TEMPLATE.format(query=query, evidence=evidence)

        # Truncate user prompt if too long
        if len(user_prompt) > self._max_input_chars:
            user_prompt = user_prompt[: self._max_input_chars - 50] + "\n\n[TRUNCATED]"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": 1000,
            "temperature": 0.3,
        }

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(
                    f"{self._api_base}/chat/completions",
                    json=payload,
                )

                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < self._max_retries:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS * (attempt + 1))
                    continue

                response.raise_for_status()
                break

            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)
                    continue
                raise SynthesisError(f"LLM request timed out after {self._timeout}s") from exc

            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code in _RETRYABLE_STATUS_CODES and attempt < self._max_retries:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                raise SynthesisError(f"LLM API error: {exc.response.status_code}") from exc

            except httpx.RequestError as exc:
                last_error = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)
                    continue
                raise SynthesisError(f"LLM request failed: {exc}") from exc
        else:
            if last_error:
                raise SynthesisError(f"LLM request failed after retries: {last_error}") from last_error

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            raise SynthesisError("Empty LLM response")

        # Truncate output if too long
        if len(content) > self._max_output_chars:
            content = content[: self._max_output_chars]

        return self._parse_llm_response(content, sources)

    def _build_evidence(self, sources: list[RankedSource]) -> str:
        """Build compact evidence text for LLM."""
        parts: list[str] = []
        total_chars = 0

        for source in sources:
            text = source.document.text or ""
            # Limit per-source text
            text = text[:2000]
            entry = f"[{source.source_id}] {source.document.title}\n{text}\n"

            if total_chars + len(entry) > self._max_input_chars:
                break

            parts.append(entry)
            total_chars += len(entry)

        return "\n".join(parts)

    def _parse_llm_response(
        self,
        content: str,
        sources: list[RankedSource],
    ) -> list[ResearchFinding]:
        """Parse LLM response into findings. Validate citation ids."""
        valid_ids = {s.source_id for s in sources}
        findings: list[ResearchFinding] = []

        # Split into paragraphs and treat each as a finding
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        for para in paragraphs:
            # Skip lines that look like headers or labels
            if para.startswith("#") or para.startswith("**Sources") or para.startswith("---"):
                continue

            # Extract citation ids [n] from text
            cited_ids = [int(n) for n in re.findall(r"\[(\d+)\]", para)]

            # Filter to only valid citation ids — reject hallucinated citations
            valid_cited = [cid for cid in cited_ids if cid in valid_ids]
            hallucinated = set(cited_ids) - set(valid_cited)

            if hallucinated:
                # Remove hallucinated citation markers from text
                for fake_id in hallucinated:
                    para = para.replace(f"[{fake_id}]", f"[INVALID-{fake_id}]")

            # Skip paragraphs with no valid content after cleaning
            if not para or len(para) < 20:
                continue

            # Assign confidence based on citation quality
            if valid_cited:
                confidence = 0.7
            elif cited_ids and not valid_cited:
                # Only hallucinated citations — low confidence
                confidence = 0.3
            else:
                # No citations at all
                confidence = 0.4

            findings.append(
                ResearchFinding(
                    statement=para,
                    evidence_ids=valid_cited,
                    confidence=confidence,
                )
            )

        return findings if findings else []

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
