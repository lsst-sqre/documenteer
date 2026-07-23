"""Tests for the Ook intersphinx inventory cache client."""

from __future__ import annotations

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
