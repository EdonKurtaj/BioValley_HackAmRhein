"""Interfaces: the contracts between the parts of this project.

This file is the single source of truth for how the parts fit together:
the data models passed between modules and the functions each part must offer.
Features are built against these contracts, so people can work in parallel.

Keep it small. Every change adds one line to docs/decisions.md in the same commit.
Additive changes (new optional field, new function) can happen in a feature branch.
Breaking changes (rename, remove, change a signature) go in a small iface/ pull request
that updates all callers. Docstrings here are the documentation; link, don't copy.
Use the domain's words (docs/glossary.md). See $hack-interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Data models: what flows between the parts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Record:
    """One input row after loading and validation.

    Replace with the real domain object (e.g. Batch, Sample, Room, Case).
    """

    id: str
    value: float


@dataclass(frozen=True)
class Finding:
    """The result of applying the domain rules to one record."""

    record_id: str
    status: str  # "ok" | "warning" | "fail"
    reason: str  # plain-language explanation shown to the user


# Columns an input CSV must have. The loader validates against this.
INPUT_COLUMNS: tuple[str, ...] = ("id", "value")


# ---------------------------------------------------------------------------
# Component contracts: what each part must offer
# ---------------------------------------------------------------------------


@runtime_checkable
class Loader(Protocol):
    """Reads raw input and returns validated records."""

    def load(self, path: str) -> list[Record]:
        """Load the file at `path`. Raises ValueError with a user-readable message on bad input."""
        ...


@runtime_checkable
class RuleEngine(Protocol):
    """Applies the domain rules (thresholds come from config/, not code)."""

    def evaluate(self, records: list[Record]) -> list[Finding]:
        """Return exactly one Finding per record, in the same order."""
        ...
