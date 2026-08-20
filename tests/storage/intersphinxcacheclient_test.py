"""Tests for the Ook intersphinx inventory cache client."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_responses  # noqa: F401
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout
from responses import RequestsMock, matchers

from documenteer.storage.intersphinxcacheclient import (
    IntersphinxCacheClient,
    IntersphinxCacheServerError,
    IntersphinxCacheUnauthorizedError,
    IntersphinxCacheUnreachableError,
)

BASE_URL = "https://roundtable.lsst.cloud/ook"

INVENTORY_URL = "https://docs.python.org/3/objects.inv"
"""An example origin ``objects.inv`` URL to fetch from the cache."""

INVENTORY_BYTES = b"# Sphinx inventory version 2\nbinary-payload\x00\x01\x02"
"""Opaque inventory bytes the cache returns, treated as an opaque blob."""

MOVED_URL = "https://pydantic.dev/docs/validation/latest/objects.inv"
"""Where a permanently-moved inventory URL now lives (a real instance:
``https://docs.pydantic.dev/latest/objects.inv`` 301s to this)."""


def test_get_inventory_success(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 200 response returns the raw inventory bytes, sending the origin
    URL as the ``url`` query parameter and a bearer token header.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.not_modified is False
    assert result.content == INVENTORY_BYTES
    assert result.etag is None
    assert len(responses.calls) == 1
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"
    assert "If-None-Match" not in api_request.headers
    assert api_request.url is not None
    query = parse_qs(urlparse(api_request.url).query)
    assert query["url"] == [INVENTORY_URL]


def test_get_inventory_returns_etag(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 200 response with an ETag header surfaces the ETag alongside the
    inventory bytes.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
        headers={"ETag": '"abc123"'},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.not_modified is False
    assert result.content == INVENTORY_BYTES
    assert result.etag == '"abc123"'


def test_get_inventory_returns_cache_status(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 200 response's ``X-Ook-Inventory-Cache-Status`` header is surfaced
    verbatim as ``cache_status``.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Cache-Status": "miss"},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.cache_status == "miss"


def test_get_inventory_conditional_not_modified(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """Passing an ETag sends ``If-None-Match``; a 304 response signals
    not-modified with no body and echoes the requested ETag back.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        status=304,
        match=[matchers.header_matcher({"If-None-Match": '"abc123"'})],
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL, etag='"abc123"')

    assert result.not_modified is True
    assert result.content is None
    assert result.etag == '"abc123"'
    api_request = responses.calls[0].request
    assert api_request.headers["If-None-Match"] == '"abc123"'


def test_not_modified_returns_cache_status(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 304 response also carries Ook's cache-status header, so a
    revalidation that transfers no body still reports how Ook served it.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        status=304,
        headers={"X-Ook-Inventory-Cache-Status": "hit"},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL, etag='"abc123"')

    assert result.not_modified is True
    assert result.cache_status == "hit"


def test_missing_cache_status_header_is_none(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """Against an older Ook that sends no cache-status header, the fetch
    result reports `None` rather than raising.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.cache_status is None


def test_get_inventory_returns_date_fetched(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 200 response's ``X-Ook-Inventory-Date-Fetched`` header is parsed into
    a timezone-aware datetime.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Date-Fetched": "2026-08-18T17:58:24Z"},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.date_fetched == datetime(2026, 8, 18, 17, 58, 24, tzinfo=UTC)


def test_not_modified_returns_date_fetched(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 304 response also carries Ook's fetch-time header. This is the only
    freshness signal a client that just revalidates ever sees, so it must be
    read on this branch too, not only on the 200.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        status=304,
        headers={"X-Ook-Inventory-Date-Fetched": "2026-08-18T17:58:24Z"},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL, etag='"abc123"')

    assert result.not_modified is True
    assert result.date_fetched == datetime(2026, 8, 18, 17, 58, 24, tzinfo=UTC)


def test_missing_date_fetched_header_is_none(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """Against an older Ook that sends no fetch-time header, the fetch result
    reports `None` rather than raising.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.date_fetched is None


@pytest.mark.parametrize(
    "value",
    ["not a timestamp", "", "2026-13-45T99:99:99Z", "1755539904"],
)
def test_unparseable_date_fetched_is_none(
    responses: RequestsMock, monkeypatch: Any, value: str
) -> None:
    """A malformed fetch-time header yields `None` without raising: a header
    Ook gets wrong must never be able to fail a documentation build.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Date-Fetched": value},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.date_fetched is None
    assert result.content == INVENTORY_BYTES


def test_naive_date_fetched_is_read_as_utc(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A fetch-time value with no offset is read as UTC rather than left
    naive, so comparing it with the build machine's clock cannot raise.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Date-Fetched": "2026-08-18T17:58:24"},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.date_fetched == datetime(2026, 8, 18, 17, 58, 24, tzinfo=UTC)


def test_get_inventory_returns_permanent_redirect(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 200 response's ``X-Ook-Inventory-Permanent-Redirect`` header is
    surfaced as the URL the requested inventory has permanently moved to.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Permanent-Redirect": MOVED_URL},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.permanent_redirect_url == MOVED_URL


def test_not_modified_returns_permanent_redirect(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 304 response also carries Ook's permanent-redirect header, so a
    build that holds current bytes and only revalidates still learns that
    its configured URL has moved.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        status=304,
        headers={"X-Ook-Inventory-Permanent-Redirect": MOVED_URL},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL, etag='"abc123"')

    assert result.not_modified is True
    assert result.permanent_redirect_url == MOVED_URL


def test_missing_permanent_redirect_header_is_none(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """Absence of the header is how Ook says an inventory URL has not moved,
    so an older Ook that never sends it behaves exactly as today.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.permanent_redirect_url is None


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_permanent_redirect_is_none(
    responses: RequestsMock, monkeypatch: Any, value: str
) -> None:
    """A header that is present but blank reads as "not moved" rather than as
    an empty destination: a header Ook gets wrong must never be reported to an
    author as somewhere to move their configuration to.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
        content_type="application/octet-stream",
        headers={"X-Ook-Inventory-Permanent-Redirect": value},
    )

    client = IntersphinxCacheClient()
    result = client.get_inventory(INVENTORY_URL)

    assert result.permanent_redirect_url is None
    assert result.content == INVENTORY_BYTES


def test_missing_token(monkeypatch: Any) -> None:
    """Without OOK_TOKEN, the client raises the unauthorized error before
    making a request.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)

    client = IntersphinxCacheClient()
    with pytest.raises(IntersphinxCacheUnauthorizedError, match="OOK_TOKEN"):
        client.get_inventory(INVENTORY_URL)


@pytest.mark.parametrize("status", [401, 403])
def test_unauthorized(
    responses: RequestsMock, monkeypatch: Any, status: int
) -> None:
    """An HTTP 401/403 response maps to the unauthorized error."""
    monkeypatch.setenv("OOK_TOKEN", "expired-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        json={"detail": "Unauthorized"},
        status=status,
    )

    client = IntersphinxCacheClient()
    with pytest.raises(IntersphinxCacheUnauthorizedError):
        client.get_inventory(INVENTORY_URL)


def test_unreachable_connection_error(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A connection error maps to the unreachable error."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=RequestsConnectionError("Connection refused"),
    )

    client = IntersphinxCacheClient()
    with pytest.raises(IntersphinxCacheUnreachableError):
        client.get_inventory(INVENTORY_URL)


def test_unreachable_timeout(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A request timeout maps to the unreachable error."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=RequestsTimeout("Timed out"),
    )

    client = IntersphinxCacheClient()
    with pytest.raises(IntersphinxCacheUnreachableError):
        client.get_inventory(INVENTORY_URL)


@pytest.mark.parametrize("status", [500, 502, 503])
def test_server_error(
    responses: RequestsMock, monkeypatch: Any, status: int
) -> None:
    """An HTTP 5xx response (including Ook's 502 for a cold miss with the
    origin down) maps to the distinct server error.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        json={"detail": "upstream unavailable"},
        status=status,
    )

    client = IntersphinxCacheClient()
    with pytest.raises(IntersphinxCacheServerError):
        client.get_inventory(INVENTORY_URL)


def test_base_url_override(responses: RequestsMock, monkeypatch: Any) -> None:
    """The service base URL is configurable (trailing slash tolerated)."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        "https://roundtable-dev.lsst.cloud/ook/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
    )

    client = IntersphinxCacheClient(
        base_url="https://roundtable-dev.lsst.cloud/ook/"
    )
    result = client.get_inventory(INVENTORY_URL)
    assert result.content == INVENTORY_BYTES


def test_explicit_token_argument(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """An explicit token argument overrides the environment variable."""
    monkeypatch.delenv("OOK_TOKEN", raising=False)
    responses.get(
        f"{BASE_URL}/intersphinx/inventory",
        body=INVENTORY_BYTES,
        status=200,
    )

    client = IntersphinxCacheClient(token="explicit-token")
    result = client.get_inventory(INVENTORY_URL)

    assert result.content == INVENTORY_BYTES
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer explicit-token"
