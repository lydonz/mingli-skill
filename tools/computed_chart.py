"""Canonical chart record shared by public MingLi entry points."""
from __future__ import annotations

from typing import Any


class ComputedChart(dict[str, Any]):
    """A dict-compatible chart produced by ``engine.compute_chart``.

    Keeping the record dict-compatible preserves existing toolkit contracts
    while making the shared-chart boundary explicit for new code.
    """
