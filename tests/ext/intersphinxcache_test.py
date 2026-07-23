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

from documenteer.ext.intersphinxcache import CACHE_DIRNAME

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


@pytest.mark.sphinx(
    "html",
    testroot="intersphinx-cache-oddkey",
    srcdir="intersphinx-cache-oddkey",
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
