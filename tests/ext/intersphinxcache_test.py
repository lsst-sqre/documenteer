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

from documenteer.ext.intersphinxcache import CACHE_DIRNAME, _inventory_filename

OOK_BASE_URL = "https://roundtable.lsst.cloud/ook"
INVENTORY_ENDPOINT = f"{OOK_BASE_URL}/intersphinx/inventory"

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

    # Ook was never contacted.
    assert not any(
        (call.request.url or "").startswith(INVENTORY_ENDPOINT)
        for call in responses.calls
    )
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

    # Ook was never contacted.
    assert not any(
        (call.request.url or "").startswith(INVENTORY_ENDPOINT)
        for call in responses.calls
    )


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
    the [sphinx.intersphinx_cache] settings through to its config values.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)

    app = _make_app(make_app, app_params)

    assert "documenteer.ext.intersphinxcache" in app.extensions
    assert app.config.documenteer_intersphinx_cache_use_service is True
    assert app.config.documenteer_intersphinx_cache_service_url == (
        OOK_BASE_URL
    )
    assert app.config.documenteer_intersphinx_cache_disk_cache_ttl == 600


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
