"""The per-build summary of how each intersphinx inventory was obtained."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

__all__ = [
    "DISK_CACHE_DETAIL",
    "NO_FETCH_TIME_DETAIL",
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

NO_FETCH_TIME_DETAIL = "fetch time unavailable"
"""What an Ook-served row says when Ook sent no usable fetch time.

Saying so is deliberate: a row with no fetch time says it has none rather
than showing a placeholder that would read as an age. This mirrors Ook's own
choice to omit the header entirely for an inventory it has not fetched,
unlike the standard ``Age`` header, whose ``0`` fallback would report a copy
of unknown age as freshly fetched.
"""

_MINUTE = 60
_HOUR = 60 * _MINUTE
_DAY = 24 * _HOUR


def _format_timestamp(when: datetime) -> str:
    """Render a fetch time as the RFC 3339 UTC instant Ook records.

    Always rendered in UTC, whatever offset the value carries, so every row's
    absolute timestamp is directly comparable with Ook's own logs.
    """
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_age(age: timedelta) -> str:
    """Humanize an age in the largest whole unit that fits.

    An age at or below one minute — including a negative one, which means the
    fetch time is ahead of the build machine's clock — reads ``just now``
    rather than as a negative duration or a spuriously precise second count:
    two clocks disagreeing is not something to report to a documentation
    author as an age.
    """
    seconds = age.total_seconds()
    if seconds < _MINUTE:
        return "just now"
    if seconds < _HOUR:
        return _plural(int(seconds // _MINUTE), "minute")
    if seconds < _DAY:
        return _plural(int(seconds // _HOUR), "hour")
    return _plural(int(seconds // _DAY), "day")


def _plural(count: int, unit: str) -> str:
    """Render ``count`` of ``unit`` as an English relative age."""
    suffix = "" if count == 1 else "s"
    return f"{count} {unit}{suffix} ago"


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

    date_fetched: datetime | None = None
    """When Ook last confirmed this inventory with its origin, or `None` when
    Ook sent no usable fetch time (or was never asked)."""


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

    def render(self, *, now: datetime | None = None) -> list[str]:
        """Render the summary block.

        Parameters
        ----------
        now
            The instant to measure each row's fetch time against. Defaults to
            the current time; tests inject a fixed value so the relative ages
            they assert do not depend on the wall clock.

        Returns
        -------
        list
            The block's lines, or an empty list when no entry was recorded
            so the caller logs nothing at all.
        """
        if not self._entries:
            return []
        if now is None:
            now = datetime.now(tz=UTC)
        name_width = max(len(entry.name) for entry in self._entries)
        status_width = max(len(entry.status) for entry in self._entries)
        return [
            REPORT_HEADING,
            *(
                self._render_entry(entry, name_width, status_width, now)
                for entry in self._entries
            ),
        ]

    @classmethod
    def _render_entry(
        cls,
        entry: InventoryReportEntry,
        name_width: int,
        status_width: int,
        now: datetime,
    ) -> str:
        """Render one row, padding the name and status columns so the
        annotations line up.

        A row that explains itself with a ``detail`` — the TTL fast path or a
        fallback — keeps that detail and reports no fetch time: Ook either was
        not asked or did not serve the inventory, so there is no fetch to
        report. Every other row came from Ook, so it reports the time Ook last
        confirmed the inventory, or says that time is unavailable.
        """
        name = f"{entry.name:<{name_width}}"
        status = f"{entry.status:<{status_width}}"
        annotation = (
            f"({entry.detail})"
            if entry.detail is not None
            else cls._render_fetch_time(entry.date_fetched, now)
        )
        return f"  {name}  {status}  {annotation}"

    @staticmethod
    def _render_fetch_time(when: datetime | None, now: datetime) -> str:
        """Render an Ook-served row's fetch time as an absolute instant plus
        a relative age.

        The absolute value is the anchor for correlating a row with Ook's own
        logs; the relative one is what a reader actually eyeballs.
        """
        if when is None:
            return NO_FETCH_TIME_DETAIL
        return f"fetched {_format_timestamp(when)} ({_format_age(now - when)})"
