"""Tests for the intersphinx inventory prefetch report."""

from __future__ import annotations

from documenteer.services.intersphinxreport import (
    DISK_CACHE_DETAIL,
    STATUS_DIRECT_FETCH,
    STATUS_DISK_CACHE,
    STATUS_SERVED,
    InventoryPrefetchReport,
    InventoryReportEntry,
)


def test_empty_report_renders_no_lines() -> None:
    """A report with no entries renders nothing, so a build that considered
    no mapping entry logs no block at all.
    """
    report = InventoryPrefetchReport()

    assert report.render() == []


def test_ook_status_renders_verbatim() -> None:
    """An Ook cache status is rendered exactly as Ook sent it, under a
    heading that names what the block reports.
    """
    report = InventoryPrefetchReport()
    report.add(InventoryReportEntry(name="python", status="hit"))

    assert report.render() == [
        "Intersphinx inventory prefetch summary (Ook cache status):",
        "  python  hit",
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

    assert report.render()[1] == (
        "  python  direct fetch (Ook could not be reached)"
    )


def test_disk_cache_status_says_ook_was_not_contacted() -> None:
    """The TTL fast path's status reads ``disk cache`` and its stock detail
    says Ook was not contacted, so the row is not mistaken for an Ook answer.
    """
    report = InventoryPrefetchReport()
    report.add(
        InventoryReportEntry(
            name="python",
            status=STATUS_DISK_CACHE,
            detail=DISK_CACHE_DETAIL,
        )
    )

    assert report.render()[1] == "  python  disk cache (Ook was not contacted)"


def test_served_status_for_an_ook_without_the_header() -> None:
    """An Ook answer with no cache-status header is reported as ``served``,
    the status the extension substitutes for a `None` header value.
    """
    report = InventoryPrefetchReport()
    report.add(InventoryReportEntry(name="python", status=STATUS_SERVED))

    assert report.render()[1] == "  python  served"


def test_entries_render_in_the_order_they_were_added() -> None:
    """Rows keep insertion order — the extension adds them while iterating
    ``intersphinx_mapping``, so the block matches the author's own config
    file order rather than being sorted.
    """
    report = InventoryPrefetchReport()
    report.add(InventoryReportEntry(name="zulu", status="hit"))
    report.add(InventoryReportEntry(name="alpha", status="miss"))
    report.add(InventoryReportEntry(name="mike", status="stale"))

    assert report.render()[1:] == [
        "  zulu   hit",
        "  alpha  miss",
        "  mike   stale",
    ]
