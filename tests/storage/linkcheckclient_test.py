"""Tests for the Ook link-check service client."""

from __future__ import annotations

import json
from typing import Any

import pytest
import pytest_responses  # noqa: F401
from requests.exceptions import ConnectionError as RequestsConnectionError
from responses import RequestsMock

from documenteer.storage.linkcheckclient import (
    CheckRunStatus,
    CheckUrlStatus,
    LinkCheckClient,
    LinkCheckRequest,
    LinkCheckTimeoutError,
    LinkCheckUnauthorizedError,
    LinkCheckUnreachableError,
    SubmittedUrl,
)

BASE_URL = "https://roundtable.lsst.cloud/ook"


def make_check_payload(
    *,
    check_id: int = 42,
    status: str = "complete",
    urls: list[dict[str, Any]] | None = None,
    summary: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Create a LinkCheck response payload matching the Ook API."""
    if urls is None:
        urls = [
            {
                "url": "https://example.com/page",
                "status": "ok",
                "status_code": 200,
                "redirect_status_code": None,
                "redirect_url": None,
                "error": None,
                "checked_at": "2026-07-06T12:00:00Z",
            }
        ]
    if summary is None:
        summary = {"ok": len(urls)}
    return {
        "id": check_id,
        "self_url": f"{BASE_URL}/linkcheck/checks/{check_id}",
        "ltd_slug": "example",
        "default_branch": True,
        "status": status,
        "date_created": "2026-07-06T12:00:00Z",
        "date_completed": (
            "2026-07-06T12:01:00Z" if status == "complete" else None
        ),
        "summary": summary,
        "urls": urls,
    }


def test_submit_check(responses: RequestsMock, monkeypatch: Any) -> None:
    """The client POSTs the submission with bearer auth and parses the
    LinkCheck response.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        json=make_check_payload(),
        status=201,
    )

    client = LinkCheckClient()
    request = LinkCheckRequest(
        ltd_slug="example",
        default_branch=True,
        urls=[
            SubmittedUrl(url="https://example.com/page", paths=["index"]),
        ],
    )
    check = client.submit_check(request)

    assert check.id == 42
    assert check.status is CheckRunStatus.complete
    assert check.summary.ok == 1
    assert check.urls[0].status is CheckUrlStatus.ok

    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"
    assert api_request.body is not None
    body = json.loads(api_request.body)
    assert body == {
        "ltd_slug": "example",
        "default_branch": True,
        "urls": [{"url": "https://example.com/page", "paths": ["index"]}],
    }


def test_get_check(responses: RequestsMock, monkeypatch: Any) -> None:
    """The client GETs a check by its ID."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/linkcheck/checks/42",
        json=make_check_payload(status="in_progress"),
        status=200,
    )

    client = LinkCheckClient()
    check = client.get_check(42)

    assert check.id == 42
    assert check.status is CheckRunStatus.in_progress
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"


def test_poll_check_until_complete(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """poll_check re-polls a pending check until it is complete."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    check_url = f"{BASE_URL}/linkcheck/checks/42"
    responses.get(
        check_url, json=make_check_payload(status="pending"), status=200
    )
    responses.get(
        check_url, json=make_check_payload(status="in_progress"), status=200
    )
    responses.get(
        check_url, json=make_check_payload(status="complete"), status=200
    )

    client = LinkCheckClient()
    check = client.poll_check(42, budget=5.0, initial_interval=0.01)

    assert check.status is CheckRunStatus.complete
    assert len(responses.calls) == 3


def test_poll_check_budget_exhausted(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """poll_check raises LinkCheckTimeoutError when the budget runs out."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/linkcheck/checks/42",
        json=make_check_payload(status="in_progress"),
        status=200,
    )

    client = LinkCheckClient()
    with pytest.raises(LinkCheckTimeoutError):
        client.poll_check(42, budget=0.05, initial_interval=0.01)


def test_missing_token(monkeypatch: Any) -> None:
    """Without OOK_TOKEN, the client raises LinkCheckUnauthorizedError
    before making a request.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)

    client = LinkCheckClient()
    with pytest.raises(LinkCheckUnauthorizedError, match="OOK_TOKEN"):
        client.get_check(42)


def test_unauthorized(responses: RequestsMock, monkeypatch: Any) -> None:
    """An HTTP 401 response maps to LinkCheckUnauthorizedError."""
    monkeypatch.setenv("OOK_TOKEN", "expired-token")
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        json={"detail": [{"msg": "Unauthorized", "type": "unauthorized"}]},
        status=401,
    )

    client = LinkCheckClient()
    request = LinkCheckRequest(
        ltd_slug="example", default_branch=True, urls=[]
    )
    with pytest.raises(LinkCheckUnauthorizedError):
        client.submit_check(request)


def test_unreachable(responses: RequestsMock, monkeypatch: Any) -> None:
    """A connection error maps to LinkCheckUnreachableError."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        body=RequestsConnectionError("Connection refused"),
    )

    client = LinkCheckClient()
    request = LinkCheckRequest(
        ltd_slug="example", default_branch=True, urls=[]
    )
    with pytest.raises(LinkCheckUnreachableError):
        client.submit_check(request)


def test_base_url_override(responses: RequestsMock, monkeypatch: Any) -> None:
    """The service base URL is configurable (trailing slash tolerated)."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        "https://roundtable-dev.lsst.cloud/ook/linkcheck/checks/42",
        json=make_check_payload(),
        status=200,
    )

    client = LinkCheckClient(base_url="https://roundtable-dev.lsst.cloud/ook/")
    check = client.get_check(42)
    assert check.id == 42
