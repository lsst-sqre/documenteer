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

CHECK_ID = "a1b2-c3d4-e5f6-g7h8"
"""An Ook Crockford base32 check id, treated as an opaque token."""


def make_check_payload(
    *,
    check_id: str = CHECK_ID,
    status: str = "complete",
    urls: list[dict[str, Any]] | None = None,
    summary: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Create a LinkCheck response payload matching the Ook API."""
    if urls is None:
        urls = [
            {
                "url": "https://example.com/page",
                "status": "ok" if status == "complete" else "pending",
                "status_code": 200 if status == "complete" else None,
                "redirect_status_code": None,
                "redirect_url": None,
                "error": None,
                "checked_at": (
                    "2026-07-06T12:00:00Z" if status == "complete" else None
                ),
            }
        ]
    if summary is None:
        if status == "complete":
            summary = {"ok": len(urls)}
        else:
            summary = {"pending": len(urls)}
    return {
        "id": check_id,
        "self_url": f"{BASE_URL}/linkcheck/checks/{check_id}",
        "origin_base_url": "https://example.lsst.io",
        "is_default_version": True,
        "status": status,
        "date_created": "2026-07-06T12:00:00Z",
        "date_completed": (
            "2026-07-06T12:01:00Z" if status == "complete" else None
        ),
        "summary": summary,
        "urls": urls,
    }


def make_request() -> LinkCheckRequest:
    """Create a link-check submission for testing."""
    return LinkCheckRequest(
        origin_base_url="https://example.lsst.io",
        is_default_version=True,
        urls=[
            SubmittedUrl(
                url="https://example.com/page", origin_paths=["index"]
            ),
        ],
    )


def test_submit_check_completed_at_submission(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 200 submission response carries the completed check as its body,
    which the client parses directly without any polling round-trip.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    check_url = f"{BASE_URL}/linkcheck/checks/{CHECK_ID}"
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        json=make_check_payload(),
        status=200,
        headers={"Location": check_url},
    )

    client = LinkCheckClient()
    check, poll_url = client.submit_check(make_request())

    assert check.id == CHECK_ID
    assert check.status is CheckRunStatus.complete
    assert check.origin_base_url == "https://example.lsst.io"
    assert check.is_default_version is True
    assert check.summary.ok == 1
    assert check.urls[0].status is CheckUrlStatus.ok
    assert poll_url == check_url

    # Only the POST was made: no polling round-trip.
    assert len(responses.calls) == 1
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"
    assert api_request.body is not None
    body = json.loads(api_request.body)
    assert body == {
        "origin_base_url": "https://example.lsst.io",
        "is_default_version": True,
        "urls": [
            {"url": "https://example.com/page", "origin_paths": ["index"]}
        ],
    }


def test_submit_check_accepted(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 202 submission response carries the pending check as its body;
    the client parses it and reports the Location header as the poll URL.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    check_url = f"{BASE_URL}/linkcheck/checks/{CHECK_ID}"
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        json=make_check_payload(status="pending"),
        status=202,
        headers={"Location": check_url},
    )

    client = LinkCheckClient()
    check, poll_url = client.submit_check(make_request())

    assert check.id == CHECK_ID
    assert check.status is CheckRunStatus.pending
    assert poll_url == check_url
    assert len(responses.calls) == 1


def test_submit_check_no_location_uses_self_url(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """Without a Location header, the poll URL falls back to the check
    body's self_url.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        json=make_check_payload(status="in_progress"),
        status=202,
    )

    client = LinkCheckClient()
    check, poll_url = client.submit_check(make_request())

    assert check.status is CheckRunStatus.in_progress
    assert poll_url == f"{BASE_URL}/linkcheck/checks/{CHECK_ID}"


def test_check_id_opaque_round_trip(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """The Ook Crockford base32 check id round-trips opaquely through
    submit → poll → complete, with no numeric parsing of the id.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    check_url = f"{BASE_URL}/linkcheck/checks/{CHECK_ID}"
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        json=make_check_payload(status="pending"),
        status=202,
        headers={"Location": check_url},
    )
    responses.get(
        check_url, json=make_check_payload(status="complete"), status=200
    )

    client = LinkCheckClient()
    submitted = client.submit_check(make_request())
    assert submitted.check.id == CHECK_ID
    assert submitted.poll_url == check_url

    check = client.poll_check(
        submitted.poll_url, budget=5.0, initial_interval=0.01
    )
    assert check.id == CHECK_ID
    assert check.status is CheckRunStatus.complete


def test_get_check(responses: RequestsMock, monkeypatch: Any) -> None:
    """The client GETs a check by its ID."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/linkcheck/checks/{CHECK_ID}",
        json=make_check_payload(status="in_progress"),
        status=200,
    )

    client = LinkCheckClient()
    check = client.get_check(CHECK_ID)

    assert check.id == CHECK_ID
    assert check.status is CheckRunStatus.in_progress
    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"


def test_poll_check_until_complete(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """poll_check re-polls a pending check at the poll URL until it is
    complete.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    check_url = f"{BASE_URL}/linkcheck/checks/{CHECK_ID}"
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
    check = client.poll_check(check_url, budget=5.0, initial_interval=0.01)

    assert check.status is CheckRunStatus.complete
    assert len(responses.calls) == 3


def test_poll_check_budget_exhausted(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """poll_check raises LinkCheckTimeoutError when the budget runs out."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    check_url = f"{BASE_URL}/linkcheck/checks/{CHECK_ID}"
    responses.get(
        check_url,
        json=make_check_payload(status="in_progress"),
        status=200,
    )

    client = LinkCheckClient()
    with pytest.raises(LinkCheckTimeoutError):
        client.poll_check(check_url, budget=0.05, initial_interval=0.01)


def test_missing_token(monkeypatch: Any) -> None:
    """Without OOK_TOKEN, the client raises LinkCheckUnauthorizedError
    before making a request.
    """
    monkeypatch.delenv("OOK_TOKEN", raising=False)

    client = LinkCheckClient()
    with pytest.raises(LinkCheckUnauthorizedError, match="OOK_TOKEN"):
        client.get_check(CHECK_ID)


def test_unauthorized(responses: RequestsMock, monkeypatch: Any) -> None:
    """An HTTP 401 response maps to LinkCheckUnauthorizedError."""
    monkeypatch.setenv("OOK_TOKEN", "expired-token")
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        json={"detail": [{"msg": "Unauthorized", "type": "unauthorized"}]},
        status=401,
    )

    client = LinkCheckClient()
    with pytest.raises(LinkCheckUnauthorizedError):
        client.submit_check(make_request())


def test_unreachable(responses: RequestsMock, monkeypatch: Any) -> None:
    """A connection error maps to LinkCheckUnreachableError."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(
        f"{BASE_URL}/linkcheck/checks",
        body=RequestsConnectionError("Connection refused"),
    )

    client = LinkCheckClient()
    with pytest.raises(LinkCheckUnreachableError):
        client.submit_check(make_request())


def test_checked_url_origin_paths_from_response(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A per-URL result's ``origin_paths`` are parsed from the poll
    response, carrying the pages the URL occurs on.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    payload = make_check_payload(
        urls=[
            {
                "url": "https://example.com/page",
                "status": "ok",
                "status_code": 200,
                "redirect_status_code": None,
                "redirect_url": None,
                "error": None,
                "checked_at": "2026-07-06T12:00:00Z",
                "origin_paths": ["guide", "index"],
            }
        ],
    )
    responses.get(
        f"{BASE_URL}/linkcheck/checks/{CHECK_ID}", json=payload, status=200
    )

    client = LinkCheckClient()
    check = client.get_check(CHECK_ID)

    assert check.urls[0].origin_paths == ["guide", "index"]


def test_checked_url_origin_paths_default_empty(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A per-URL result without ``origin_paths`` (a not-yet-upgraded Ook)
    defaults to an empty list rather than erroring.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    # make_check_payload's default URL omits origin_paths.
    responses.get(
        f"{BASE_URL}/linkcheck/checks/{CHECK_ID}",
        json=make_check_payload(),
        status=200,
    )

    client = LinkCheckClient()
    check = client.get_check(CHECK_ID)

    assert check.urls[0].origin_paths == []


def test_blocked_status_parses(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A URL Ook reports as ``blocked`` (bot protection, lsst-sqre/ook#290)
    parses into the ``blocked`` disposition, and the summary's ``blocked``
    count is read back without disturbing the other status counts.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    payload = make_check_payload(
        urls=[
            {
                "url": "https://example.com/page",
                "status": "blocked",
                "status_code": 403,
                "redirect_status_code": None,
                "redirect_url": None,
                "error": "403 Forbidden",
                "checked_at": "2026-07-06T12:00:00Z",
                "origin_paths": ["index"],
            }
        ],
        summary={"blocked": 1},
    )
    responses.get(
        f"{BASE_URL}/linkcheck/checks/{CHECK_ID}", json=payload, status=200
    )

    client = LinkCheckClient()
    check = client.get_check(CHECK_ID)

    assert check.urls[0].status is CheckUrlStatus.blocked
    assert check.summary.blocked == 1
    # Blocked is its own count; broken (which fails the build) stays zero.
    assert check.summary.broken == 0


def test_base_url_override(responses: RequestsMock, monkeypatch: Any) -> None:
    """The service base URL is configurable (trailing slash tolerated)."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"https://roundtable-dev.lsst.cloud/ook/linkcheck/checks/{CHECK_ID}",
        json=make_check_payload(),
        status=200,
    )

    client = LinkCheckClient(base_url="https://roundtable-dev.lsst.cloud/ook/")
    check = client.get_check(CHECK_ID)
    assert check.id == CHECK_ID
