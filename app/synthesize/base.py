"""Synthesizer base interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import RankedSource, ResearchFinding


class Synthesizer(ABC):
    """Interface for synthesis engines."""

    @abstractmethod
    async def synthesize(
        self,
        query: str,
        sources: list[RankedSource],
    ) -> list[ResearchFinding]:
        """Synthesize findings from ranked sources."""
