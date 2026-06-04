"""Extractive synthesizer — builds findings from evidence without LLM."""

from __future__ import annotations

from app.models import RankedSource, ResearchFinding
from app.synthesize.base import Synthesizer


class ExtractiveSynthesizer(Synthesizer):
    """Deterministic extractive synthesizer.

    Groups sources by relevance, extracts key sentences,
    and builds findings with citation references.
    """

    async def synthesize(
        self,
        query: str,
        sources: list[RankedSource],
    ) -> list[ResearchFinding]:
        if not sources:
            return []

        findings: list[ResearchFinding] = []
        query_words = set(query.lower().split())

        # Group by relevance tiers
        high_relevance = [s for s in sources if s.score >= 30]
        medium_relevance = [s for s in sources if 10 <= s.score < 30]

        # Build findings from high-relevance sources
        for source in high_relevance:
            sentences = _extract_relevant_sentences(source, query_words)
            if sentences:
                findings.append(
                    ResearchFinding(
                        statement=" ".join(sentences[:3]),
                        evidence_ids=[source.source_id],
                        confidence=min(source.score / 50.0, 1.0),
                    )
                )

        # If not enough findings, add medium-relevance sources
        if len(findings) < 2:
            for source in medium_relevance:
                sentences = _extract_relevant_sentences(source, query_words)
                if sentences:
                    findings.append(
                        ResearchFinding(
                            statement=" ".join(sentences[:3]),
                            evidence_ids=[source.source_id],
                            confidence=min(source.score / 50.0, 0.7),
                        )
                    )

        # If still no findings, create a generic finding per source
        if not findings:
            for source in sources[:3]:
                first_sentence = _first_sentence(source.document.text)
                if first_sentence:
                    findings.append(
                        ResearchFinding(
                            statement=first_sentence,
                            evidence_ids=[source.source_id],
                            confidence=0.3,
                            limitations=["Low relevance match — source may be tangential."],
                        )
                    )

        # Add limitations if few sources
        if len(sources) < 3:
            for f in findings:
                f.limitations.append(
                    "Limited sources available — findings may not be comprehensive."
                )

        return findings


def _extract_relevant_sentences(
    source: RankedSource,
    query_words: set[str],
) -> list[str]:
    """Extract sentences most relevant to the query."""
    text = source.document.text
    if not text:
        return []

    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
    if not sentences:
        return []

    # Score each sentence by query word overlap
    scored: list[tuple[float, str]] = []
    for sentence in sentences:
        words = set(sentence.lower().split())
        overlap = len(query_words & words)
        scored.append((overlap, sentence))

    # Sort by relevance and take top 3
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:3] if _ > 0]


def _first_sentence(text: str) -> str:
    """Get the first meaningful sentence from text."""
    if not text:
        return ""
    sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
    return sentences[0] if sentences else ""
