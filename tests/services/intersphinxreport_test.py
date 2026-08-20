"""Tests for the intersphinx inventory prefetch report."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from documenteer.services.intersphinxreport import (
    DISK_CACHE_DETAIL,
    MOVED_FLAG,
    NO_FETCH_TIME_DETAIL,
    STATUS_DIRECT_FETCH,
    STATUS_DISK_CACHE,
    STATUS_SERVED,
    InventoryPrefetchReport,
    InventoryReportEntry,
)

NOW = datetime(2026, 8, 18, 18, 24, 30, tzinfo=UTC)
"""A fixed "current" time, injected into `render` so relative ages are
deterministic rather than depending on the wall clock."""

FETCHED = datetime(2026, 8, 18, 17, 58, 24, tzinfo=UTC)
"""A fetch time 26 minutes (and 6 seconds) before `NOW`."""


def test_empty_report_renders_no_lines() -> None:
    """A report with no entries renders nothing, so a build that considered
    no mapping entry logs no block at all.
    """
    report = InventoryPrefetchReport()

    assert report.render(now=NOW) == []


def test_ook_status_renders_verbatim() -> None:
    """An Ook cache status is rendered exactly as Ook sent it, under a
    heading that names what the block reports.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(name="python", status="hit", date_fetched=FETCHED)
    )

    assert report.render(now=NOW) == [
        "Intersphinx inventory prefetch summary (Ook cache status):",
        "  python  hit  fetched 2026-08-18T17:58:24Z (26 minutes ago)",
    ]


def test_detail_is_appended_in_parentheses() -> None:
    """A row with a detail appends it in parentheses after the status, so the
    reason for a non-Ook status is on the same line.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="python",
            status=STATUS_DIRECT_FETCH,
            detail="Ook could not be reached",
        )
    )

    assert report.render(now=NOW)[1] == (
        "  python  direct fetch  (Ook could not be reached)"
    )


def test_disk_cache_status_says_ook_was_not_contacted() -> None:
    """The TTL fast path's status reads ``disk cache`` and its stock detail
    says Ook was not contacted, so the row is not mistaken for an Ook answer.
    A row that explains itself this way reports no fetch time: Ook was never
    asked, so there is nothing to report.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="python",
            status=STATUS_DISK_CACHE,
            detail=DISK_CACHE_DETAIL,
        )
    )

    assert report.render(now=NOW)[1] == (
        "  python  disk cache  (Ook was not contacted)"
    )


def test_served_status_for_an_ook_without_the_header() -> None:
    """An Ook answer with no headers at all is reported as ``served`` with its
    fetch time called out as unavailable, rather than with a placeholder or a
    bare timestamp.
    """
    report = InventoryPrefetchReport()
    report.add(InventoryReportEntry(name="python", status=STATUS_SERVED))

    assert report.render(now=NOW)[1] == (
        f"  python  served  {NO_FETCH_TIME_DETAIL}"
    )


def test_entries_render_in_the_order_they_were_added() -> None:
    """Rows keep insertion order — the extension adds them while iterating
    ``intersphinx_mapping``, so the block matches the author's own config
    file order rather than being sorted. Both columns are padded so the
    fetch times line up for scanning.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(name="zulu", status="hit", date_fetched=FETCHED)
    )
    report.add(
        InventoryReportEntry(
            name="alpha",
            status="miss",
            date_fetched=NOW - timedelta(hours=3),
        )
    )
    report.add(
        InventoryReportEntry(name="mike", status="stale", date_fetched=None)
    )

    assert report.render(now=NOW)[1:] == [
        "  zulu   hit    fetched 2026-08-18T17:58:24Z (26 minutes ago)",
        "  alpha  miss   fetched 2026-08-18T15:24:30Z (3 hours ago)",
        "  mike   stale  fetch time unavailable",
    ]


def test_future_fetch_time_renders_just_now() -> None:
    """A fetch time ahead of the build machine's clock renders as ``just
    now`` rather than as a negative duration: the two clocks disagreeing is
    not something to show the author as a negative age.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="python",
            status="hit",
            date_fetched=NOW + timedelta(minutes=5),
        )
    )

    assert report.render(now=NOW)[1] == (
        "  python  hit  fetched 2026-08-18T18:29:30Z (just now)"
    )


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (timedelta(seconds=0), "just now"),
        (timedelta(seconds=59), "just now"),
        (timedelta(seconds=60), "1 minute ago"),
        (timedelta(minutes=26, seconds=6), "26 minutes ago"),
        (timedelta(minutes=59, seconds=59), "59 minutes ago"),
        (timedelta(hours=1), "1 hour ago"),
        (timedelta(hours=23, minutes=59), "23 hours ago"),
        (timedelta(hours=25), "1 day ago"),
        (timedelta(days=9, hours=4), "9 days ago"),
    ],
)
def test_relative_age_wording(age: timedelta, expected: str) -> None:
    """Ages are humanized against the injected ``now`` in the largest unit
    that fits, singular or plural, so the reader eyeballs the age rather than
    subtracting timestamps.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="python", status="hit", date_fetched=NOW - age
        )
    )

    assert report.render(now=NOW)[1].endswith(f"({expected})")


def test_fetch_time_renders_in_utc() -> None:
    """A fetch time carrying a non-UTC offset renders as the equivalent UTC
    instant, so every row's absolute timestamp is directly comparable with
    Ook's own logs.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="python",
            status="hit",
            date_fetched=datetime(
                2026, 8, 18, 13, 58, 24, tzinfo=timezone(timedelta(hours=-4))
            ),
        )
    )

    assert report.render(now=NOW)[1] == (
        "  python  hit  fetched 2026-08-18T17:58:24Z (26 minutes ago)"
    )


def test_moved_entry_is_flagged() -> None:
    """A row whose inventory URL has permanently moved is flagged, so the
    block shows at a glance which configured URL is stale. The destination
    itself is not in the row: it belongs to the dedicated notice, which has
    room for it and for what to do about it.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="pydantic",
            status="hit",
            date_fetched=FETCHED,
            permanent_redirect_url=(
                "https://pydantic.dev/docs/validation/latest/objects.inv"
            ),
        )
    )

    (row,) = report.render(now=NOW)[1:]
    assert row == (
        "  pydantic  hit  fetched 2026-08-18T17:58:24Z (26 minutes ago)"
        f"  {MOVED_FLAG}"
    )
    assert "pydantic.dev/docs" not in row


def test_unmoved_entry_carries_no_flag_and_no_padding() -> None:
    """An entry that has not moved is unflagged, and a block that flags no
    entry at all renders exactly as it did before the flag existed — no
    trailing whitespace where a flag would have gone.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(name="python", status="hit", date_fetched=FETCHED)
    )

    assert report.render(now=NOW)[1] == (
        "  python  hit  fetched 2026-08-18T17:58:24Z (26 minutes ago)"
    )


def test_flags_line_up_across_mixed_rows() -> None:
    """With rows of differing annotation lengths, the flag column is padded
    into alignment, and the unflagged rows keep no trailing whitespace.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="pydantic",
            status="hit",
            date_fetched=FETCHED,
            permanent_redirect_url="https://example.com/moved/objects.inv",
        )
    )
    report.add(InventoryReportEntry(name="python", status=STATUS_SERVED))

    rows = report.render(now=NOW)[1:]
    assert rows == [
        "  pydantic  hit     fetched 2026-08-18T17:58:24Z (26 minutes ago)"
        f"  {MOVED_FLAG}",
        "  python    served  fetch time unavailable",
    ]


def test_a_moved_entry_with_a_detail_keeps_both() -> None:
    """A flagged row whose status explains itself with a detail keeps the
    detail *and* the flag: the two answer different questions.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="pydantic",
            status=STATUS_DISK_CACHE,
            detail=DISK_CACHE_DETAIL,
            permanent_redirect_url="https://example.com/moved/objects.inv",
        )
    )

    assert report.render(now=NOW)[1] == (
        f"  pydantic  disk cache  (Ook was not contacted)  {MOVED_FLAG}"
    )


def test_render_defaults_now_to_the_current_time() -> None:
    """``now`` is optional: the extension renders the block without threading
    a clock through, while tests inject one for deterministic ages.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="python",
            status="hit",
            date_fetched=datetime.now(tz=UTC) - timedelta(minutes=5),
        )
    )

    assert report.render()[1].endswith("(5 minutes ago)")
