"""Tests for the documenteer.ext.intersphinxcache extension."""

from __future__ import annotations

import importlib.util
import zlib
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_responses  # noqa: F401
from responses import RequestsMock, matchers
from sphinx.testing.util import SphinxTestApp

from documenteer.ext.intersphinxcache import (
    CACHE_DIRNAME,
    REDIRECT_WARNING_SUBTYPE,
    REDIRECT_WARNING_TYPE,
    _inventory_filename,
)
from documenteer.services.intersphinxreport import MOVED_FLAG, REPORT_HEADING

OOK_BASE_URL = "https://roundtable.lsst.cloud/ook"
INVENTORY_ENDPOINT = f"{OOK_BASE_URL}/intersphinx/inventory"

# Two real instances of a permanently-moved inventory URL and one that has
# not moved, used by the permanent-redirect tests below.
PYDANTIC_INV_URL = "https://docs.pydantic.dev/latest/objects.inv"
PYDANTIC_MOVED_URL = "https://pydantic.dev/docs/validation/latest/objects.inv"
PYTHON_INV_URL = "https://docs.python.org/3/objects.inv"

# Whether the guide preset's theme is importable; the guide test root builds
# the full user-guide stack (``from documenteer.conf.guide import *``), which
# pins ``html_theme = "pydata_sphinx_theme"``.
_HAS_PYDATA = importlib.util.find_spec("pydata_sphinx_theme") is not None

# Whether the technote preset's dependencies are importable; the technote
# test root builds the full technote stack
# (``from documenteer.conf.technote import *``).
_HAS_TECHNOTE_DEPS = importlib.util.find_spec("technote") is not None


def _make_inventory(
    *,
    project: str = "Test Project",
    version: str = "1.0",
    name: str = "example.func",
    location: str = "api.html#example.func",
) -> bytes:
    """Build a valid Sphinx v2 object inventory with a single ``py:function``
    entry so a cross-reference into it resolves.
    """
    header = (
        "# Sphinx inventory version 2\n"
        f"# Project: {project}\n"
        f"# Version: {version}\n"
        "# The remainder of this file is compressed using zlib.\n"
    ).encode()
    body = f"{name} py:function 1 {location} -\n".encode()
    return header + zlib.compress(body, 9)


def _inventory_locations(app: SphinxTestApp, name: str) -> tuple[Any, ...]:
    """Return the normalized inventory locations for a mapping entry.

    After ``sphinx.ext.intersphinx`` validates the mapping on
    ``config-inited``, each entry has the shape
    ``(name, (target_uri, locations))``.
    """
    return app.config.intersphinx_mapping[name][1][1]


def _make_app(make_app: Any, app_params: Any) -> SphinxTestApp:
    """Construct the test app inside the test body.

    The extension prefetches on ``config-inited``, which fires while the app
    is constructed. Building the app here — rather than depending on the
    ``app`` fixture, which constructs at fixture-setup time — ensures the
    ``responses`` mock and ``OOK_TOKEN`` are already in place when the
    prefetch runs.
    """
    args, kwargs = app_params
    return make_app(*args, **kwargs)


@pytest.mark.sphinx(
    "html", testroot="intersphinx-cache", srcdir="intersphinx-cache-happy"
)
def test_prefetch_rewrites_mapping_and_resolves(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """With OOK_TOKEN set, the extension prefetches the inventory from Ook,
    rewrites the mapping to a local file, and cross-references resolve to
    the upstream URL without any direct origin fetch.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    # The Ook API was queried for the origin objects.inv URL with bearer
    # auth from OOK_TOKEN.
    assert len(responses.calls) == 1
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"
    assert api_request.url is not None
    query = parse_qs(urlparse(api_request.url).query)
    assert query["url"] == [origin_inv_url]

    # The origin site itself was never fetched directly.
    assert not any(
        (call.request.url or "").startswith("https://example.com")
        for call in responses.calls
    )

    # The mapping's inventory location was rewritten to a local file (no
    # URL scheme) that exists on disk.
    locations = _inventory_locations(app, "testproj")
    assert len(locations) == 1
    local_path = Path(locations[0])
    assert "://" not in locations[0]
    assert local_path.is_file()

    # The target URI is left unchanged, so links resolve upstream.
    assert app.config.intersphinx_mapping["testproj"][1][0] == (
        "https://example.com/project/"
    )

    # The cross-reference resolved to the upstream URL in the built HTML.
    html = (Path(app.outdir) / "index.html").read_text()
    assert "https://example.com/project/api.html#example.func" in html


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-ttl-fastpath",
)
def test_ttl_fast_path_skips_ook_on_second_build(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A second build within disk_cache_ttl reuses the on-disk inventory
    without contacting Ook, and the mapping is still rewritten to the local
    cache file.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    # The first build fetches from Ook and writes the on-disk cache.
    app1 = _make_app(make_app, app_params)
    app1.build()
    assert len(responses.calls) == 1

    # A second build within the TTL (the default 600s) reuses the on-disk
    # inventory without contacting Ook at all.
    app2 = _make_app(make_app, app_params)
    app2.build()
    assert len(responses.calls) == 1

    # The mapping is still rewritten to the local cache file.
    locations = _inventory_locations(app2, "testproj")
    assert len(locations) == 1
    assert "://" not in locations[0]
    assert Path(locations[0]).is_file()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-ttl-disabled",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
)
def test_ttl_zero_revalidates_every_build(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """With disk_cache_ttl = 0 the fast path is disabled, so every build
    revalidates with Ook even when a fresh on-disk cache file exists.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()
    assert len(responses.calls) == 1

    # A second build contacts Ook again because the fast path is disabled.
    app2 = _make_app(make_app, app_params)
    app2.build()
    assert len(responses.calls) == 2


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-log-download",
)
def test_download_logged_at_info(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A successful cold download from Ook is reported at info level naming
    the inventory, so build logs show that the Ook cache was used (rather
    than the prefetch being silent and only intersphinx's local-file loading
    lines appearing).
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    inventory = _make_inventory()
    responses.get(
        INVENTORY_ENDPOINT,
        body=inventory,
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    # The download is reported at info level (status stream, not the warning
    # stream, so a warnings-as-errors ``-W`` build is unaffected), naming the
    # inventory and the byte count.
    status = app.status.getvalue()
    assert (
        "Downloaded the intersphinx inventory for 'testproj' from Ook "
        f"({len(inventory)} bytes)." in status
    )
    assert "Downloaded" not in app.warning.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-log-fastpath",
)
def test_ttl_fast_path_logged_at_info(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A TTL fast-path reuse (no request to Ook) is reported at info level
    naming the inventory, so build logs distinguish a cache hit from the
    extension not running at all.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    # The first build downloads and writes the on-disk cache.
    app1 = _make_app(make_app, app_params)
    app1.build()

    # The second build (within the default TTL) reuses the on-disk copy and
    # says so at info level (status stream, not the warning stream).
    app2 = _make_app(make_app, app_params)
    app2.build()
    status = app2.status.getvalue()
    assert (
        "Reusing the on-disk intersphinx inventory for 'testproj' "
        "(younger than disk_cache_ttl)." in status
    )
    assert "Reusing" not in app2.warning.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-summary-miss",
)
def test_summary_block_reports_ook_cache_status(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A build that fetches from Ook logs one summary block after the
    per-entry prefetch lines, carrying Ook's cache status for the entry.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Cache-Status": "miss"},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    # The block is on the status stream (info level), not the warning stream,
    # so a warnings-as-errors ``-W`` build is unaffected by it.
    status = app.status.getvalue()
    assert REPORT_HEADING in status
    assert "  testproj  miss" in status
    assert REPORT_HEADING not in app.warning.getvalue()

    # The block comes after the per-entry line that narrates the download.
    assert status.index("Downloaded the intersphinx inventory") < status.index(
        REPORT_HEADING
    )


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-summary-hit",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
)
def test_summary_block_reports_hit_on_revalidation(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A rebuild past the disk TTL that Ook answers from its own cache
    reports ``hit``, where the first (cold) build reported ``miss``, and
    carries the fetch time Ook sent on the 304 — the only freshness signal a
    build that only ever revalidates gets to see.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    etag = '"v1etag"'
    # The 304 (registered first) is chosen only when If-None-Match is sent;
    # the initial build has no such header and falls through to the 200.
    responses.get(
        INVENTORY_ENDPOINT,
        status=304,
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Date-Fetched": "2026-08-18T17:58:24Z",
        },
        match=[
            matchers.query_param_matcher({"url": origin_inv_url}),
            matchers.header_matcher({"If-None-Match": etag}),
        ],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": etag, "X-Ook-Inventory-Cache-Status": "miss"},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()
    assert "  testproj  miss" in app1.status.getvalue()

    app2 = _make_app(make_app, app_params)
    app2.build()
    assert (
        "  testproj  hit  fetched 2026-08-18T17:58:24Z ("
        in app2.status.getvalue()
    )


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-summary-fetched",
)
def test_summary_block_reports_the_fetch_time(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """An Ook-served row carries the absolute time Ook last confirmed the
    inventory with its origin, plus a relative age, so the author can both
    correlate with Ook's own logs and eyeball how fresh the copy is.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "miss",
            "X-Ook-Inventory-Date-Fetched": "2026-08-18T17:58:24Z",
        },
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    status = app.status.getvalue()
    # The absolute timestamp is asserted exactly; the relative age is left to
    # the report module's own tests, which inject a fixed ``now``.
    assert "  testproj  miss  fetched 2026-08-18T17:58:24Z (" in status
    assert "fetched" not in app.warning.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-summary-bad-date",
    warningiserror=True,
)
def test_unparseable_fetch_time_says_unavailable(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A malformed fetch-time header from Ook cannot fail a build: the row
    says the fetch time is unavailable and a warnings-as-errors build still
    succeeds.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "miss",
            "X-Ook-Inventory-Date-Fetched": "yesterday afternoon",
        },
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    assert "  testproj  miss  fetch time unavailable" in app.status.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-summary-disk",
)
def test_summary_block_reports_the_disk_cache_fast_path(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """An entry served from the TTL fast path reports ``disk cache`` and says
    Ook was not contacted, so the row is not mistaken for an Ook cache hit.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Cache-Status": "miss"},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()

    # The second build (within the default TTL) never contacts Ook.
    app2 = _make_app(make_app, app_params)
    app2.build()
    assert len(responses.calls) == 1
    assert (
        "  testproj  disk cache  (Ook was not contacted)"
        in app2.status.getvalue()
    )


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-summary-served",
)
def test_summary_block_reports_served_without_the_header(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """Against an Ook that sends no cache-status header, the row reads
    ``served`` and the build completes without a traceback.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    assert "  testproj  served" in app.status.getvalue()
    assert "Traceback" not in app.warning.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-multi",
    srcdir="intersphinx-cache-summary-fallback",
)
def test_summary_block_reports_a_fallback_with_its_reason(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """An entry whose fetch failed reports ``direct fetch`` with the reason
    and no fetch time (there was no successful fetch to report), while the
    entry Ook served reports its own. The block keeps ``intersphinx_mapping``
    order rather than sorting.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    proja_inv_url = "https://a.example.com/objects.inv"
    projb_inv_url = "https://b.example.com/objects.inv"
    # Ook fails for proja (a cold-miss 502) but serves projb from its cache.
    responses.get(
        INVENTORY_ENDPOINT,
        json={"detail": "upstream unavailable"},
        status=502,
        match=[matchers.query_param_matcher({"url": proja_inv_url})],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Date-Fetched": "2026-08-18T17:58:24Z",
        },
        match=[matchers.query_param_matcher({"url": projb_inv_url})],
    )
    # proja falls back to a direct origin fetch, which succeeds.
    responses.get(proja_inv_url, body=_make_inventory(), status=200)

    app = _make_app(make_app, app_params)
    app.build()

    status = app.status.getvalue()
    block = status[status.index(REPORT_HEADING) :].splitlines()[:3]
    assert block[:2] == [
        REPORT_HEADING,
        "  proja  direct fetch  (Ook returned a server error)",
    ]
    assert block[2].startswith(
        "  projb  hit           fetched 2026-08-18T17:58:24Z ("
    )


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-empty",
    srcdir="intersphinx-cache-summary-empty",
)
def test_no_block_when_the_mapping_is_empty(
    make_app: Any,
    app_params: Any,
    monkeypatch: Any,
) -> None:
    """With nothing to prefetch, the extension logs no summary block at all
    rather than an empty one.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")

    app = _make_app(make_app, app_params)
    app.build()

    assert REPORT_HEADING not in app.status.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-local",
    srcdir="intersphinx-cache-summary-local",
)
def test_local_entries_are_absent_from_the_block(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A mapping entry with a local target URI, or an inventory location that
    is already a local path, is not prefetched and so gets no row: the block
    reports only the entries the extension actually considered.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Cache-Status": "miss"},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    status = app.status.getvalue()
    block = status[status.index(REPORT_HEADING) :].splitlines()[:2]
    assert block == [
        REPORT_HEADING,
        "  remoteproj  miss  fetch time unavailable",
    ]
    assert "  localtarget" not in status
    assert "  localinv" not in status

    # Only the remote entry was fetched from Ook; the local ones were left
    # entirely alone.
    assert len(responses.calls) == 1


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-summary-warningiserror",
    warningiserror=True,
)
def test_summary_block_does_not_fail_a_warnings_as_errors_build(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """The block is logged at info level, so a ``-W`` build succeeds with it
    present — none of what it reports is the author's to fix.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Cache-Status": "miss"},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    assert "  testproj  miss" in app.status.getvalue()


def _redirect_notices(app: SphinxTestApp) -> list[str]:
    """Return every permanent-redirect notice on the build's status stream.

    Each notice is a single line, so scoping an assertion to one of them
    keeps a check that the notice does *not* name some file from being
    defeated by an unrelated line elsewhere in the same build.
    """
    return [
        line
        for line in app.status.getvalue().splitlines()
        if "has permanently moved" in line
    ]


def _summary_rows(app: SphinxTestApp, count: int) -> list[str]:
    """Return the first ``count`` rows of the build's summary block."""
    status = app.status.getvalue()
    return status[status.index(REPORT_HEADING) :].splitlines()[1 : count + 1]


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-guide",
    srcdir="intersphinx-cache-redirect-guide",
    warningiserror=True,
)
def test_permanent_redirect_notice_names_the_guide_config(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """When Ook reports that an inventory URL has permanently moved, the
    build says so at info level — naming the mapping key, the URL the project
    configures, where it now lives, and the guide's own configuration file to
    change — and flags that row in the summary block. A mapping entry that
    has not moved gets neither the notice nor the flag. Escalation is off by
    default, so the notice is info, not a warning, this ``-W`` build
    succeeds, and both entries are still rewritten to their local cache
    files.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Date-Fetched": "2026-08-18T17:58:24Z",
            "X-Ook-Inventory-Permanent-Redirect": PYDANTIC_MOVED_URL,
        },
        match=[matchers.query_param_matcher({"url": PYDANTIC_INV_URL})],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Date-Fetched": "2026-08-18T17:58:24Z",
        },
        match=[matchers.query_param_matcher({"url": PYTHON_INV_URL})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    # Exactly one entry moved, so exactly one notice, naming both URLs.
    (notice,) = _redirect_notices(app)
    assert "'pydantic'" in notice
    assert PYDANTIC_INV_URL in notice
    assert PYDANTIC_MOVED_URL in notice
    assert "[sphinx.intersphinx.projects]" in notice
    assert "documenteer.toml" in notice
    assert PYTHON_INV_URL not in notice
    # Info, not a warning: escalation defaults off, so this build ran with -W
    # and still succeeded.
    assert (
        app.config.documenteer_intersphinx_cache_warn_on_permanent_redirect
        is False
    )
    assert "permanently moved" not in app.warning.getvalue()
    assert app.statuscode == 0

    rows = _summary_rows(app, 2)
    assert rows[0].startswith(
        "  pydantic  hit  fetched 2026-08-18T17:58:24Z ("
    )
    assert rows[0].endswith(f"  {MOVED_FLAG}")
    assert rows[1].startswith(
        "  python    hit  fetched 2026-08-18T17:58:24Z ("
    )
    assert MOVED_FLAG not in rows[1]

    # Both entries are still rewritten to the local cache file: a moved URL
    # is reported, not routed around.
    for name in ("pydantic", "python"):
        location = _inventory_locations(app, name)[0]
        assert "://" not in location
        assert Path(location).is_file()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-technote",
    srcdir="intersphinx-cache-redirect-technote",
)
def test_permanent_redirect_notice_names_the_technote_config(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A technote author is sent to the keys of their own configuration file,
    never to a ``documenteer.toml`` their project does not have.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Permanent-Redirect": PYDANTIC_MOVED_URL,
        },
        match=[matchers.query_param_matcher({"url": PYDANTIC_INV_URL})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    (notice,) = _redirect_notices(app)
    assert PYDANTIC_INV_URL in notice
    assert PYDANTIC_MOVED_URL in notice
    assert "[technote.sphinx.intersphinx.projects]" in notice
    assert "technote.toml" in notice
    assert "documenteer.toml" not in notice
    assert _summary_rows(app, 1)[0].endswith(f"  {MOVED_FLAG}")


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-redirect-bare",
)
def test_permanent_redirect_notice_without_a_config_file(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A project with neither TOML file beside its ``conf.py`` is pointed at
    the Sphinx setting it actually has, naming no file it does not.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    moved_url = "https://example.net/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "miss",
            "X-Ook-Inventory-Permanent-Redirect": moved_url,
        },
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    (notice,) = _redirect_notices(app)
    assert "'testproj'" in notice
    assert origin_inv_url in notice
    assert moved_url in notice
    assert "intersphinx_mapping" in notice
    assert "conf.py" in notice
    assert "documenteer.toml" not in notice
    assert "technote.toml" not in notice


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-redirect-304",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
    warningiserror=True,
)
def test_permanent_redirect_reported_on_revalidation(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """The notice rides Ook's ``304`` as well as its ``200``: a second build
    forced past the disk-cache TTL, which transfers no body at all, still
    tells the author their configured URL has moved and still flags the row.
    The mapping is rewritten to the local file on this branch too, and the
    ``-W`` build succeeds.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    moved_url = "https://example.net/project/objects.inv"
    etag = '"v1etag"'
    # The 304 (registered first) is chosen only when If-None-Match is sent;
    # the initial build has no such header and falls through to the 200.
    responses.get(
        INVENTORY_ENDPOINT,
        status=304,
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Permanent-Redirect": moved_url,
        },
        match=[
            matchers.query_param_matcher({"url": origin_inv_url}),
            matchers.header_matcher({"If-None-Match": etag}),
        ],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": etag, "X-Ook-Inventory-Cache-Status": "miss"},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()
    assert _redirect_notices(app1) == []

    app2 = _make_app(make_app, app_params)
    app2.build()

    (notice,) = _redirect_notices(app2)
    assert origin_inv_url in notice
    assert moved_url in notice
    assert "permanently moved" not in app2.warning.getvalue()
    assert _summary_rows(app2, 1)[0].endswith(f"  {MOVED_FLAG}")

    location = _inventory_locations(app2, "testproj")[0]
    assert "://" not in location
    assert Path(location).is_file()


def _redirect_warnings(app: SphinxTestApp) -> list[str]:
    """Return every permanent-redirect notice on the build's warning stream.

    The mirror of `_redirect_notices` for the opt-in escalated form, so a
    test can assert which stream the notice landed on rather than only that
    the text exists somewhere.
    """
    return [
        line
        for line in app.warning.getvalue().splitlines()
        if "has permanently moved" in line
    ]


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-guide",
    srcdir="intersphinx-cache-redirect-warn-guide",
    confoverrides={
        "documenteer_intersphinx_cache_warn_on_permanent_redirect": True
    },
    warningiserror=True,
)
def test_permanent_redirect_warning_opt_in_fails_a_strict_build(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A project that opts into escalation gets the redirect notice as a
    warning — carrying the suppress_warnings key — and its ``-W`` build fails.

    The escalation governs only the dedicated notice: the summary block stays
    at info level, so opting in never turns the whole block into a build
    failure. Nothing else changes — the wording still names the guide's own
    configuration file, and both entries are still rewritten to their local
    cache files.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Permanent-Redirect": PYDANTIC_MOVED_URL,
        },
        match=[matchers.query_param_matcher({"url": PYDANTIC_INV_URL})],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Cache-Status": "hit"},
        match=[matchers.query_param_matcher({"url": PYTHON_INV_URL})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    # The moved entry warns, once, on the warning stream and not the status
    # stream, with the wording and the suppress_warnings key.
    (warning,) = _redirect_warnings(app)
    assert "'pydantic'" in warning
    assert PYDANTIC_INV_URL in warning
    assert PYDANTIC_MOVED_URL in warning
    assert "[sphinx.intersphinx.projects]" in warning
    assert f"[{REDIRECT_WARNING_TYPE}.{REDIRECT_WARNING_SUBTYPE}]" in warning
    assert _redirect_notices(app) == []

    # The build ran with -W and failed on that warning.
    assert app.statuscode == 1

    # Only the notice escalated: the summary block is still on the status
    # stream at info level, with its row still flagged.
    assert REPORT_HEADING not in app.warning.getvalue()
    rows = _summary_rows(app, 2)
    assert rows[0].endswith(f"  {MOVED_FLAG}")
    assert MOVED_FLAG not in rows[1]

    # The prefetch is unchanged: a moved URL is reported, not routed around.
    for name in ("pydantic", "python"):
        location = _inventory_locations(app, name)[0]
        assert "://" not in location
        assert Path(location).is_file()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-technote",
    srcdir="intersphinx-cache-redirect-warn-technote",
    confoverrides={
        "documenteer_intersphinx_cache_warn_on_permanent_redirect": True
    },
    warningiserror=True,
)
def test_permanent_redirect_warning_opt_in_from_technote_conf_py(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A technote reaches the escalation through the Sphinx config value in
    its ``conf.py`` — Documenteer adds no keys to ``technote.toml`` — and the
    escalated notice still names the technote's own configuration file.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Permanent-Redirect": PYDANTIC_MOVED_URL,
        },
        match=[matchers.query_param_matcher({"url": PYDANTIC_INV_URL})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    (warning,) = _redirect_warnings(app)
    assert PYDANTIC_MOVED_URL in warning
    assert "[technote.sphinx.intersphinx.projects]" in warning
    assert "documenteer.toml" not in warning
    assert app.statuscode == 1


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-guide",
    srcdir="intersphinx-cache-redirect-suppressed",
    confoverrides={
        "documenteer_intersphinx_cache_warn_on_permanent_redirect": True,
        "suppress_warnings": [
            f"{REDIRECT_WARNING_TYPE}.{REDIRECT_WARNING_SUBTYPE}"
        ],
    },
    warningiserror=True,
)
def test_permanent_redirect_warning_can_be_suppressed(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """The escalated notice carries a warning type/subtype, so a project that
    knows about one moved inventory can silence just that warning and keep
    its ``-W`` build passing without giving up the escalation elsewhere.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={
            "X-Ook-Inventory-Cache-Status": "hit",
            "X-Ook-Inventory-Permanent-Redirect": PYDANTIC_MOVED_URL,
        },
        match=[matchers.query_param_matcher({"url": PYDANTIC_INV_URL})],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Cache-Status": "hit"},
        match=[matchers.query_param_matcher({"url": PYTHON_INV_URL})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    assert _redirect_warnings(app) == []
    assert app.statuscode == 0
    # The summary block still reports the move; only the warning is silenced.
    assert _summary_rows(app, 1)[0].endswith(f"  {MOVED_FLAG}")


def _etag_sidecar(inv_path: Path) -> Path:
    """Return the ETag sidecar path for a cached ``.inv`` file."""
    return inv_path.with_name(inv_path.name + ".etag")


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-etag-304",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
)
def test_revalidation_304_reuses_disk_bytes(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """After the TTL expires, a revalidation that returns 304 reuses the
    on-disk inventory (no body transferred) and rewrites the mapping to the
    local file.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    etag = '"v1etag"'
    inventory = _make_inventory()
    # The 304 (registered first) is chosen only when If-None-Match is sent;
    # the initial build has no such header and falls through to the 200.
    responses.get(
        INVENTORY_ENDPOINT,
        status=304,
        match=[
            matchers.query_param_matcher({"url": origin_inv_url}),
            matchers.header_matcher({"If-None-Match": etag}),
        ],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=inventory,
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": etag},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    # First build fetches a 200 with an ETag and writes the .inv + sidecar.
    app1 = _make_app(make_app, app_params)
    app1.build()
    assert len(responses.calls) == 1
    inv_path = Path(_inventory_locations(app1, "testproj")[0])
    sidecar = _etag_sidecar(inv_path)
    assert sidecar.read_text() == etag

    # Second build revalidates with If-None-Match and gets a 304.
    app2 = _make_app(make_app, app_params)
    app2.build()
    assert len(responses.calls) == 2
    assert responses.calls[1].request.headers["If-None-Match"] == etag

    # The on-disk bytes are reused unchanged and the mapping still points at
    # the local file; the sidecar is preserved.
    locations = _inventory_locations(app2, "testproj")
    assert "://" not in locations[0]
    assert Path(locations[0]) == inv_path
    assert inv_path.read_bytes() == inventory
    assert sidecar.read_text() == etag


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-log-304",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
)
def test_revalidation_304_logged_at_info(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A revalidation answered with 304 Not Modified is reported at info
    level naming the inventory, so build logs show that Ook was consulted
    and the on-disk copy is current.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    etag = '"v1etag"'
    # The 304 (registered first) is chosen only when If-None-Match is sent;
    # the initial build has no such header and falls through to the 200.
    responses.get(
        INVENTORY_ENDPOINT,
        status=304,
        match=[
            matchers.query_param_matcher({"url": origin_inv_url}),
            matchers.header_matcher({"If-None-Match": etag}),
        ],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": etag},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()

    # The second build revalidates, gets a 304, and says so at info level
    # (status stream, not the warning stream).
    app2 = _make_app(make_app, app_params)
    app2.build()
    status = app2.status.getvalue()
    assert (
        "The intersphinx inventory for 'testproj' is unchanged on Ook "
        "(HTTP 304 Not Modified); reusing the on-disk copy." in status
    )
    assert "unchanged on Ook" not in app2.warning.getvalue()


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-unconditional-304",
)
def test_unconditional_304_falls_back(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A protocol-violating 304 answered to an unconditional request (no
    cached inventory, so no If-None-Match was sent) is treated as a fallback:
    the entry is left untouched with an info-level log rather than mapped to a
    nonexistent local file.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    # The very first build has no cached .inv/sidecar, so it sends no
    # If-None-Match; a misbehaving server answers 304 anyway.
    responses.get(
        INVENTORY_ENDPOINT,
        status=304,
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    # The fallback is reported at info level (not a warning, so a
    # warnings-as-errors ``-W`` build does not fail on the misbehavior) and
    # names the inventory, and the entry is left untouched (its inventory
    # location is still None) so stock intersphinx fetches the origin directly.
    status = app.status.getvalue()
    assert "testproj" in status
    assert "304 Not Modified" in status
    assert "304 Not Modified" not in app.warning.getvalue()
    assert _inventory_locations(app, "testproj") == (None,)
    # No local cache file was mapped in, so nothing points at a possibly
    # nonexistent path.
    cache_dir = Path(app.doctreedir).parent / CACHE_DIRNAME
    assert not any(cache_dir.glob("*.inv")) if cache_dir.exists() else True


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-etag-200",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
)
def test_revalidation_200_replaces_inv_and_sidecar(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A revalidation that returns 200 replaces both the .inv file and the
    ETag sidecar.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    inv_v1 = _make_inventory(version="1.0")
    inv_v2 = _make_inventory(version="2.0")
    # When If-None-Match "v1" is sent, the server returns fresh bytes + v2.
    responses.get(
        INVENTORY_ENDPOINT,
        body=inv_v2,
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": '"v2"'},
        match=[
            matchers.query_param_matcher({"url": origin_inv_url}),
            matchers.header_matcher({"If-None-Match": '"v1"'}),
        ],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=inv_v1,
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": '"v1"'},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()
    inv_path = Path(_inventory_locations(app1, "testproj")[0])
    sidecar = _etag_sidecar(inv_path)
    assert inv_path.read_bytes() == inv_v1
    assert sidecar.read_text() == '"v1"'

    app2 = _make_app(make_app, app_params)
    app2.build()
    assert len(responses.calls) == 2

    # Both the inventory bytes and the sidecar are replaced with the new copy.
    assert inv_path.read_bytes() == inv_v2
    assert sidecar.read_text() == '"v2"'


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-no-etag",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
)
def test_no_etag_server_full_fetch_no_sidecar(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """Against a server that returns no ETag, behavior is today's: a full
    fetch on every TTL miss, no sidecar written, and no warnings.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()
    assert len(responses.calls) == 1
    inv_path = Path(_inventory_locations(app1, "testproj")[0])
    assert not _etag_sidecar(inv_path).exists()

    # A second build (TTL disabled) fetches the full body again; still no
    # sidecar and no warnings.
    app2 = _make_app(make_app, app_params)
    app2.build()
    assert len(responses.calls) == 2
    assert not _etag_sidecar(inv_path).exists()
    # The extension itself emits no warning (the only lines in the warning
    # stream are Sphinx's own multi-app node-registration noise from building
    # two apps in one process, which does not occur in a real build).
    warning = app2.warning.getvalue()
    assert "Could not" not in warning
    assert "intersphinx inventory" not in warning


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-etag-cleared",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
)
def test_200_without_etag_clears_stale_sidecar(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A 200 response without an ETag clears any stale sidecar left by a
    previous ETag-bearing response (e.g. after a server downgrade).
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    # The revalidation (If-None-Match "v1") is answered by a downgraded server
    # with a 200 that carries no ETag header.
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(version="2.0"),
        status=200,
        content_type="application/octet-stream",
        match=[
            matchers.query_param_matcher({"url": origin_inv_url}),
            matchers.header_matcher({"If-None-Match": '"v1"'}),
        ],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(version="1.0"),
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": '"v1"'},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()
    inv_path = Path(_inventory_locations(app1, "testproj")[0])
    sidecar = _etag_sidecar(inv_path)
    assert sidecar.read_text() == '"v1"'

    app2 = _make_app(make_app, app_params)
    app2.build()
    assert len(responses.calls) == 2
    # The stale sidecar is removed and the mapping still points at the file.
    assert not sidecar.exists()
    assert Path(_inventory_locations(app2, "testproj")[0]) == inv_path


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-etag-error",
    confoverrides={"documenteer_intersphinx_cache_disk_cache_ttl": 0},
)
def test_revalidation_error_leaves_mapping_untouched(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A client error during revalidation leaves the mapping entry untouched
    with an info-level log, and the build still succeeds via a direct origin
    fetch.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    # The revalidation fails with a client error. A 404 (not a force-listed
    # 5xx) is answered on the first attempt without the retry session
    # consuming the fallback 200, keeping the scenario deterministic.
    responses.get(
        INVENTORY_ENDPOINT,
        json={"detail": "not found"},
        status=404,
        match=[
            matchers.query_param_matcher({"url": origin_inv_url}),
            matchers.header_matcher({"If-None-Match": '"v1"'}),
        ],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": '"v1"'},
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app1 = _make_app(make_app, app_params)
    app1.build()

    app2 = _make_app(make_app, app_params)
    app2.build()

    # The build succeeds and the fallback is reported at info level (not a
    # warning, so a warnings-as-errors ``-W`` build does not fail), naming the
    # inventory. The mapping entry is left untouched (its inventory location
    # is still None), so stock intersphinx is responsible for the origin,
    # exactly as without the service.
    status = app2.status.getvalue()
    assert "testproj" in status
    assert "Could not prefetch" in status
    assert "Could not prefetch" not in app2.warning.getvalue()
    assert _inventory_locations(app2, "testproj") == (None,)


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-multi",
    srcdir="intersphinx-cache-fallback",
)
def test_per_inventory_fallback(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """When Ook fails for one inventory, the build reports the fallback at
    info level naming it and that entry falls back to a direct origin fetch,
    while other inventories still use the cache.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    proja_inv_url = "https://a.example.com/objects.inv"
    projb_inv_url = "https://b.example.com/objects.inv"
    # Ook fails for proja (a cold-miss 502) but serves projb.
    responses.get(
        INVENTORY_ENDPOINT,
        json={"detail": "upstream unavailable"},
        status=502,
        match=[matchers.query_param_matcher({"url": proja_inv_url})],
    )
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": projb_inv_url})],
    )
    # proja falls back to a direct origin fetch, which succeeds.
    responses.get(proja_inv_url, body=_make_inventory(), status=200)

    app = _make_app(make_app, app_params)
    app.build()

    # The fallback is reported at info level (not as a warning, so a
    # warnings-as-errors ``-W`` build does not fail on Ook degradation),
    # naming the failed inventory.
    status = app.status.getvalue()
    assert "proja" in status
    assert "Could not prefetch" in status
    assert "Could not prefetch" not in app.warning.getvalue()

    # projb was rewritten to a local cache file; proja was left untouched
    # (its inventory location is still None, so intersphinx fetches the
    # origin directly).
    projb_locations = _inventory_locations(app, "projb")
    assert len(projb_locations) == 1
    assert "://" not in projb_locations[0]
    assert Path(projb_locations[0]).is_file()
    assert _inventory_locations(app, "proja") == (None,)

    # Ook was queried for both inventories (proja's cold-miss 502 is retried
    # by the client, so it may appear more than once).
    ook_query_urls = {
        parse_qs(urlparse(str(call.request.url)).query)["url"][0]
        for call in responses.calls
        if (call.request.url or "").startswith(INVENTORY_ENDPOINT)
    }
    assert ook_query_urls == {proja_inv_url, projb_inv_url}

    # Only proja was fetched directly from its origin (the fallback); projb
    # was served entirely from the cache and never fetched directly.
    assert any(
        (call.request.url or "") == proja_inv_url for call in responses.calls
    )
    assert not any(
        (call.request.url or "") == projb_inv_url for call in responses.calls
    )


def test_inventory_filename_keys_on_name_and_origin_url() -> None:
    """The cache filename hash includes the resolved origin URL, so changing
    an entry's URL (while keeping the same key) yields a different filename —
    the new URL misses the cache and is fetched immediately rather than served
    a stale inventory for up to one TTL window.
    """
    name = "proj"
    url_a = "https://a.example.com/objects.inv"
    url_b = "https://b.example.com/objects.inv"

    # Deterministic for identical inputs.
    assert _inventory_filename(name, url_a) == _inventory_filename(name, url_a)
    # A changed origin URL changes the filename.
    assert _inventory_filename(name, url_a) != _inventory_filename(name, url_b)
    # A changed key still changes the filename (distinct keys never collide).
    assert _inventory_filename("other", url_a) != _inventory_filename(
        name, url_a
    )
    # The stem is still the sanitized key and the suffix is still .inv.
    assert _inventory_filename(name, url_a).startswith("proj-")
    assert _inventory_filename(name, url_a).endswith(".inv")


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-oddkey",
    srcdir="intersphinx-cache-oddkey-sanitize",
)
def test_mapping_key_with_path_separator_is_sanitized(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """A mapping key containing a path separator does not raise out of the
    config-inited handler: the cache filename is sanitized and the entry is
    still rewritten to a local file inside the cache directory.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )

    app = _make_app(make_app, app_params)
    app.build()

    # The entry was rewritten to a local file that exists on disk.
    locations = _inventory_locations(app, "proj/sub")
    assert len(locations) == 1
    assert "://" not in locations[0]
    local_path = Path(locations[0])
    assert local_path.is_file()

    # The filename is a single path component under the cache directory with
    # the separator sanitized away (no nested "proj/sub" directory).
    assert local_path.parent.name == CACHE_DIRNAME
    assert "/" not in local_path.name
    assert local_path.name.startswith("proj_sub-")


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-write-failure",
)
def test_write_failure_falls_back(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """An OSError while writing the prefetched inventory does not fail the
    build: the entry is left untouched with the fallback reported at info
    level, and stock intersphinx fetches the origin directly.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    origin_inv_url = "https://example.com/project/objects.inv"
    responses.get(
        INVENTORY_ENDPOINT,
        body=_make_inventory(),
        status=200,
        content_type="application/octet-stream",
        match=[matchers.query_param_matcher({"url": origin_inv_url})],
    )
    # The entry falls back to a direct origin fetch, which succeeds.
    responses.get(origin_inv_url, body=_make_inventory(), status=200)

    # Fail only writes into the extension's cache directory, so Sphinx's own
    # build writes are unaffected.
    real_write_bytes = Path.write_bytes

    def _failing_write_bytes(self: Path, data: bytes) -> int:
        if CACHE_DIRNAME in self.parts:
            raise OSError("simulated disk failure")
        return real_write_bytes(self, data)

    monkeypatch.setattr(Path, "write_bytes", _failing_write_bytes)

    app = _make_app(make_app, app_params)
    app.build()

    # The fallback is reported at info level (not as a warning, so a
    # warnings-as-errors ``-W`` build does not fail on a cache write
    # failure), naming the inventory.
    status = app.status.getvalue()
    assert "testproj" in status
    assert "Could not write" in status
    assert "Could not write" not in app.warning.getvalue()

    # The entry was left untouched, so intersphinx fetched the origin
    # directly and the cross-reference still resolved upstream.
    assert _inventory_locations(app, "testproj") == (None,)
    assert any(
        (call.request.url or "") == origin_inv_url for call in responses.calls
    )
    html = (Path(app.outdir) / "index.html").read_text()
    assert "https://example.com/project/api.html#example.func" in html


@pytest.mark.sphinx(
    "html", testroot="intersphinx-cache", srcdir="intersphinx-cache-no-token"
)
def test_no_token_is_noop(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """With OOK_TOKEN unset, the extension no-ops: Ook is never contacted and
    stock intersphinx behavior (a direct origin fetch) is unchanged.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)
    # Stock intersphinx fetches the origin directly.
    responses.get(
        "https://example.com/project/objects.inv",
        body=_make_inventory(),
        status=200,
    )

    app = _make_app(make_app, app_params)
    app.build()

    # The mapping is untouched: the inventory location is still None.
    assert _inventory_locations(app, "testproj") == (None,)

    # Ook was never contacted and no summary block was logged.
    assert not any(
        (call.request.url or "").startswith(INVENTORY_ENDPOINT)
        for call in responses.calls
    )
    assert REPORT_HEADING not in app.status.getvalue()
    # Stock intersphinx resolved the cross-reference from the direct fetch.
    html = (Path(app.outdir) / "index.html").read_text()
    assert "https://example.com/project/api.html#example.func" in html


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache",
    srcdir="intersphinx-cache-disabled",
    confoverrides={"documenteer_intersphinx_cache_use_service": False},
)
def test_use_service_false_disables_extension(
    make_app: Any,
    app_params: Any,
    responses: RequestsMock,
    monkeypatch: Any,
) -> None:
    """With use_service disabled, the extension no-ops even when OOK_TOKEN is
    set: Ook is never contacted and stock intersphinx behavior is unchanged.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # Stock intersphinx fetches the origin directly.
    responses.get(
        "https://example.com/project/objects.inv",
        body=_make_inventory(),
        status=200,
    )

    app = _make_app(make_app, app_params)
    app.build()

    # The mapping is untouched despite the token being present.
    assert _inventory_locations(app, "testproj") == (None,)

    # Ook was never contacted and no summary block was logged.
    assert not any(
        (call.request.url or "").startswith(INVENTORY_ENDPOINT)
        for call in responses.calls
    )
    assert REPORT_HEADING not in app.status.getvalue()


@pytest.mark.skipif(
    not _HAS_PYDATA, reason="pydata_sphinx_theme is not installed"
)
@pytest.mark.sphinx("html", testroot="guide", srcdir="guide-intersphinx-cache")
def test_guide_preset_registers_extension(
    make_app: Any,
    app_params: Any,
    monkeypatch: Any,
) -> None:
    """The guide preset registers the intersphinxcache extension and wires
    the [sphinx.intersphinx.cache] settings through to its config values.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)

    app = _make_app(make_app, app_params)

    assert "documenteer.ext.intersphinxcache" in app.extensions
    assert app.config.documenteer_intersphinx_cache_use_service is True
    assert app.config.documenteer_intersphinx_cache_service_url == (
        OOK_BASE_URL
    )
    assert app.config.documenteer_intersphinx_cache_disk_cache_ttl == 600
    assert (
        app.config.documenteer_intersphinx_cache_warn_on_permanent_redirect
        is False
    )


@pytest.mark.skipif(
    not _HAS_TECHNOTE_DEPS, reason="technote dependencies are not installed"
)
@pytest.mark.sphinx(
    "html",
    testroot="technote-linkcheck-service",
    srcdir="technote-intersphinx-cache",
)
def test_technote_preset_registers_extension(
    make_app: Any,
    app_params: Any,
    monkeypatch: Any,
) -> None:
    """The technote preset registers the intersphinxcache extension with the
    extension's default settings.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)

    app = _make_app(make_app, app_params)

    assert "documenteer.ext.intersphinxcache" in app.extensions
    assert app.config.documenteer_intersphinx_cache_use_service is True
    assert app.config.documenteer_intersphinx_cache_service_url == (
        OOK_BASE_URL
    )
    assert app.config.documenteer_intersphinx_cache_disk_cache_ttl == 600
    # A technote overrides this in conf.py; Documenteer adds no keys to
    # technote.toml, so the preset leaves the extension's default in place.
    assert (
        app.config.documenteer_intersphinx_cache_warn_on_permanent_redirect
        is False
    )
