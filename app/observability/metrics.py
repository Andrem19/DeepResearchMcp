"""Simple metrics counters for observability."""

from __future__ import annotations

from collections import defaultdict


class Metrics:
    """Thread-unsafe simple metrics counter. Good enough for single-process server."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    def get(self, name: str) -> int:
        return self._counters.get(name, 0)

    def snapshot(self) -> dict[str, int]:
        return dict(self._counters)

    def reset(self) -> None:
        self._counters.clear()


# Global metrics instance
metrics = Metrics()
