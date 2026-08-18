"""The per-build summary of how each intersphinx inventory was obtained."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DISK_CACHE_DETAIL",
    "REPORT_HEADING",
    "STATUS_DIRECT_FETCH",
    "STATUS_DISK_CACHE",
    "STATUS_SERVED",
    "InventoryPrefetchReport",
    "InventoryReportEntry",
]

REPORT_HEADING = "Intersphinx inventory prefetch summary (Ook cache status):"
"""Heading line introducing the summary block."""

STATUS_DISK_CACHE = "disk cache"
"""Status for an entry served from the client-side disk-cache TTL fast path,
where Ook was never contacted."""

STATUS_DIRECT_FETCH = "direct fetch"
"""Status for an entry left untouched, so stock intersphinx fetches the
origin directly. The ``detail`` carries the reason."""

STATUS_SERVED = "served"
"""Status for an entry Ook answered without sending a cache-status header
(an older Ook), where the fact that Ook answered is all that is known."""

DISK_CACHE_DETAIL = "Ook was not contacted"
"""Stock ``detail`` for a `STATUS_DISK_CACHE` row."""


@dataclass(frozen=True)
class InventoryReportEntry:
    """One mapping entry's row in the inventory prefetch summary."""

    name: str
    """The ``intersphinx_mapping`` key this row reports on."""

    status: str
    """How the inventory was obtained."""

    detail: str | None = None
    """Extra context for the row, or `None` when the status speaks for
    itself."""


class InventoryPrefetchReport:
    """An accumulating summary of how each intersphinx inventory was
    obtained during one build.

    Entries are rendered in the order they were added, which the extension
    drives from ``intersphinx_mapping`` — the order the author sees in their
    own configuration file.
    """

    def __init__(self) -> None:
        self._entries: list[InventoryReportEntry] = []

    def add(self, entry: InventoryReportEntry) -> None:
        """Record one mapping entry's outcome.

        Parameters
        ----------
        entry
            The row to append to the summary.
        """
        self._entries.append(entry)

    def render(self) -> list[str]:
        """Render the summary block.

        Returns
        -------
        list
            The block's lines, or an empty list when no entry was recorded
            so the caller logs nothing at all.
        """
        if not self._entries:
            return []
        width = max(len(entry.name) for entry in self._entries)
        return [
            REPORT_HEADING,
            *(self._render_entry(entry, width) for entry in self._entries),
        ]

    @staticmethod
    def _render_entry(entry: InventoryReportEntry, width: int) -> str:
        """Render one row, padding the name so the statuses line up."""
        line = f"  {entry.name:<{width}}  {entry.status}"
        if entry.detail is not None:
            line = f"{line} ({entry.detail})"
        return line
