"""Tests for the local link checker used to recheck bot-blocked URLs."""

from __future__ import annotations

import pytest
import pytest_responses  # noqa: F401
from requests.exceptions import ConnectionError as RequestsConnectionError
from responses import RequestsMock
from sphinx.builders.linkcheck import DEFAULT_REQUEST_HEADERS

from documenteer.storage.locallinkchecker import (
    SPHINX_USER_AGENT,
    LocalLinkChecker,
)


def test_head_success_records_status_code(responses: RequestsMock) -> None:
    """A URL that answers HEAD with a 200 is a successful local
    observation carrying the HTTP status code and no error.
    """
    responses.head("https://example.com/page", status=200)

    result = LocalLinkChecker(delay=0.0).check_url("https://example.com/page")

    assert result.url == "https://example.com/page"
    assert result.status_code == 200
    assert result.error is None
    assert result.is_ok is True


def test_sends_sphinx_request_headers(responses: RequestsMock) -> None:
    """The local check sends Sphinx linkcheck's default browser-prefixed
    User-Agent and its Accept header, so a site that serves the build a
    different response than it serves Ook is exercised the same way
    Sphinx's built-in checker would exercise it.
    """
    responses.head("https://example.com/page", status=200)

    LocalLinkChecker(delay=0.0).check_url("https://example.com/page")

    headers = responses.calls[0].request.headers
    assert headers["User-Agent"] == SPHINX_USER_AGENT
    assert headers["User-Agent"].startswith("Mozilla/5.0 ")
    assert "Sphinx/" in headers["User-Agent"]
    assert headers["Accept"] == DEFAULT_REQUEST_HEADERS["Accept"]


def test_head_failure_falls_back_to_get(responses: RequestsMock) -> None:
    """A URL whose HEAD fails is retried with a GET, mirroring Sphinx's
    HEAD-then-GET retrieval ladder: many servers reject HEAD outright yet
    serve the page fine.
    """
    responses.head("https://example.com/page", status=405)
    responses.get("https://example.com/page", status=200)

    result = LocalLinkChecker(delay=0.0).check_url("https://example.com/page")

    assert [call.request.method for call in responses.calls] == ["HEAD", "GET"]
    assert result.status_code == 200
    assert result.is_ok is True


def test_exhausted_ladder_records_error(responses: RequestsMock) -> None:
    """A URL that fails both retrieval methods is a failed observation
    that keeps the last response's status code as its evidence.
    """
    responses.head("https://example.com/page", status=404)
    responses.get("https://example.com/page", status=404)

    result = LocalLinkChecker(delay=0.0).check_url("https://example.com/page")

    assert result.is_ok is False
    assert result.status_code == 404
    assert result.error is not None
    assert "404" in result.error


def test_redirect_is_captured(responses: RequestsMock) -> None:
    """A URL that resolves through a redirect records the redirect's own
    status code and the destination it landed on.
    """
    responses.head(
        "https://example.com/page",
        status=301,
        headers={"Location": "https://example.com/new"},
    )
    responses.head("https://example.com/new", status=200)

    result = LocalLinkChecker(delay=0.0).check_url("https://example.com/page")

    assert result.is_ok is True
    assert result.status_code == 200
    assert result.redirect_status_code == 301
    assert result.redirect_url == "https://example.com/new"


def test_no_response_leaves_status_code_null(responses: RequestsMock) -> None:
    """A URL that never answers has no status code to report; the
    transport error is the only evidence.
    """
    responses.head(
        "https://example.com/page", body=RequestsConnectionError("boom")
    )
    responses.get(
        "https://example.com/page", body=RequestsConnectionError("boom")
    )

    result = LocalLinkChecker(delay=0.0).check_url("https://example.com/page")

    assert result.is_ok is False
    assert result.status_code is None
    assert result.error == "boom"


def test_check_urls_is_sequential_and_polite(
    responses: RequestsMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """URLs are checked one at a time, in order, with a politeness delay
    between them — but no delay before the first, so a single URL is
    checked without waiting at all.
    """
    urls = ["https://example.com/a", "https://example.com/b"]
    for url in urls:
        responses.head(url, status=200)
    sleeps: list[float] = []
    monkeypatch.setattr(
        "documenteer.storage.locallinkchecker.time.sleep", sleeps.append
    )

    results = LocalLinkChecker(delay=0.25).check_urls(urls)

    assert [result.url for result in results] == urls
    assert [call.request.url for call in responses.calls] == urls
    assert sleeps == [0.25]
