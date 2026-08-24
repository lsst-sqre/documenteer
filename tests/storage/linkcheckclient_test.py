"""Tests for the Ook link-check service client."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_responses  # noqa: F401
from requests.exceptions import ConnectionError as RequestsConnectionError
from responses import RequestsMock

from documenteer.storage.linkcheckclient import (
    CheckRunStatus,
    CheckUrlStatus,
    ContributedResult,
    ContributionEnvironment,
    ContributionProvider,
    ContributionRejectionReason,
    LinkCheckClient,
    LinkCheckContributionError,
    LinkCheckMalformedResponseError,
    LinkCheckRequest,
    LinkCheckTimeoutError,
    LinkCheckUnauthorizedError,
    LinkCheckUnreachableError,
    SubmittedUrl,
)
from documenteer.version import __version__

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
                "date_checked": (
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


CONTRIBUTIONS_URL = f"{BASE_URL}/linkcheck/checks/{CHECK_ID}/contributions"

CHECKED_AT = datetime(2026, 7, 6, 12, 0, tzinfo=UTC)
"""When the contributing client observed its results."""


def make_contribution_payload(
    *,
    accepted: list[dict[str, Any]] | None = None,
    rejected: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a contribution report payload matching the Ook API."""
    if accepted is None:
        accepted = [{"url": "https://example.com/guarded", "status": "ok"}]
    return {
        "check_id": CHECK_ID,
        "provenance": {
            "provider": "github_actions",
            "repository": "lsst-sqre/documenteer",
            "run_id": "42",
            "workflow_ref": (
                "lsst-sqre/documenteer/.github/workflows/ci.yaml@refs/heads/main"
            ),
            "run_url": (
                "https://github.com/lsst-sqre/documenteer/actions/runs/42"
            ),
            "checker_version": "documenteer 2.5.0",
        },
        "accepted": accepted,
        "rejected": rejected if rejected is not None else [],
    }


def make_environment() -> ContributionEnvironment:
    """Create the advisory environment block for testing."""
    return ContributionEnvironment(
        repository="lsst-sqre/documenteer",
        run_url="https://github.com/lsst-sqre/documenteer/actions/runs/42",
        checker_version="documenteer 2.5.0",
    )


def make_results() -> list[ContributedResult]:
    """Create the per-URL local observations to contribute."""
    return [
        ContributedResult(
            url="https://example.com/guarded",
            status_code=200,
            date_checked=CHECKED_AT,
        )
    ]


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
                "date_checked": "2026-07-06T12:00:00Z",
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


def test_checked_url_date_checked_parses(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A per-URL result's check time is read from Ook's ``date_checked``
    field — the ``date_``-prefixed spelling lsst-sqre/ook#366 normalized
    every datetime-valued link-check field onto.
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
                "date_checked": "2026-07-06T12:00:00Z",
                "origin_paths": ["index"],
            }
        ],
    )
    responses.get(
        f"{BASE_URL}/linkcheck/checks/{CHECK_ID}", json=payload, status=200
    )

    client = LinkCheckClient()
    check = client.get_check(CHECK_ID)

    assert check.urls[0].date_checked == CHECKED_AT


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
                "date_checked": "2026-07-06T12:00:00Z",
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


def test_contribute_results(responses: RequestsMock, monkeypatch: Any) -> None:
    """A contribution POSTs the local observations with the OIDC id token
    in the body — the endpoint's provenance attestation — alongside the
    Gafaelfawr bearer token the ingress requires, and reports back the
    status each accepted URL reached.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(
        CONTRIBUTIONS_URL, json=make_contribution_payload(), status=200
    )

    client = LinkCheckClient()
    report = client.contribute_results(
        CHECK_ID,
        make_results(),
        id_token="a.b.c",
        environment=make_environment(),
    )

    assert report.check_id == CHECK_ID
    assert report.provenance.repository == "lsst-sqre/documenteer"
    assert report.provenance.run_id == "42"
    assert [entry.url for entry in report.accepted] == [
        "https://example.com/guarded"
    ]
    assert report.accepted[0].status is CheckUrlStatus.ok
    assert report.rejected == []

    api_request = responses.calls[0].request
    assert api_request.headers["Authorization"] == "Bearer test-token"
    assert api_request.body is not None
    assert json.loads(api_request.body) == {
        "id_token": "a.b.c",
        "environment": {
            "provider": "github_actions",
            "repository": "lsst-sqre/documenteer",
            "run_url": (
                "https://github.com/lsst-sqre/documenteer/actions/runs/42"
            ),
            "checker_version": "documenteer 2.5.0",
        },
        "results": [
            {
                "url": "https://example.com/guarded",
                "status_code": 200,
                "redirect_status_code": None,
                "redirect_url": None,
                "error": None,
                "date_checked": "2026-07-06T12:00:00Z",
            }
        ],
    }


def test_contribute_results_partial_accept(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """The service applies a batch entry by entry, so a report can carry
    both applied and declined entries; each declined entry parses with the
    typed reason the caller reports per URL.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(
        CONTRIBUTIONS_URL,
        json=make_contribution_payload(
            rejected=[
                {
                    "url": "https://example.com/open",
                    "reason": "not_blocked",
                    "message": "Ook resolved this URL itself.",
                }
            ],
        ),
        status=200,
    )

    client = LinkCheckClient()
    report = client.contribute_results(
        CHECK_ID,
        make_results(),
        id_token="a.b.c",
        environment=make_environment(),
    )

    assert len(report.accepted) == 1
    assert [entry.url for entry in report.rejected] == [
        "https://example.com/open"
    ]
    rejection = report.rejected[0]
    assert rejection.reason is ContributionRejectionReason.not_blocked
    assert rejection.message == "Ook resolved this URL itself."


def test_contribute_results_unknown_rejection_reason(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A rejection reason this client does not know about still parses.

    Rejection reasons are an open diagnostic vocabulary the service can
    extend. An unrecognized one arrives as its plain string so the caller
    can still report it, rather than costing the whole report its parse.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(
        CONTRIBUTIONS_URL,
        json=make_contribution_payload(
            rejected=[
                {
                    "url": "https://example.com/open",
                    "reason": "some_future_reason",
                    "message": "Something this client has not heard of.",
                }
            ],
        ),
        status=200,
    )

    client = LinkCheckClient()
    report = client.contribute_results(
        CHECK_ID,
        make_results(),
        id_token="a.b.c",
        environment=make_environment(),
    )

    assert report.rejected[0].reason == "some_future_reason"


def test_contribute_results_retries_bad_gateway(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 502 means the service could not reach GitHub's signing keys to
    verify the id token, which it documents as worth retrying; the
    contribution is resent after a backoff and succeeds.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    sleeps: list[float] = []
    monkeypatch.setattr(
        "documenteer.storage.linkcheckclient.time.sleep", sleeps.append
    )
    responses.post(CONTRIBUTIONS_URL, json={"detail": "JWKS"}, status=502)
    responses.post(
        CONTRIBUTIONS_URL, json=make_contribution_payload(), status=200
    )

    client = LinkCheckClient()
    report = client.contribute_results(
        CHECK_ID,
        make_results(),
        id_token="a.b.c",
        environment=make_environment(),
    )

    assert len(report.accepted) == 1
    assert len(responses.calls) == 2
    assert sleeps == [0.5]


def test_contribute_results_retry_exhausted(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A service that keeps answering 502 outlasts the retry ladder: the
    contribution is retried three times, on a backoff that doubles, and
    then surfaces as the typed error the caller downgrades to a warning.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    sleeps: list[float] = []
    monkeypatch.setattr(
        "documenteer.storage.linkcheckclient.time.sleep", sleeps.append
    )
    responses.post(CONTRIBUTIONS_URL, json={"detail": "JWKS"}, status=502)

    client = LinkCheckClient()
    with pytest.raises(LinkCheckContributionError, match="4 attempts"):
        client.contribute_results(
            CHECK_ID,
            make_results(),
            id_token="a.b.c",
            environment=make_environment(),
        )

    # The original attempt plus three retries.
    assert len(responses.calls) == 4
    assert sleeps == [0.5, 1.0, 2.0]


def test_contribute_results_retries_connection_error(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A connection failure is as transient as a 502, so it is retried on
    the same ladder rather than abandoning the contribution outright.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    monkeypatch.setattr(
        "documenteer.storage.linkcheckclient.time.sleep", lambda _: None
    )
    responses.post(
        CONTRIBUTIONS_URL, body=RequestsConnectionError("Connection refused")
    )
    responses.post(
        CONTRIBUTIONS_URL, json=make_contribution_payload(), status=200
    )

    client = LinkCheckClient()
    report = client.contribute_results(
        CHECK_ID,
        make_results(),
        id_token="a.b.c",
        environment=make_environment(),
    )

    assert len(report.accepted) == 1
    assert len(responses.calls) == 2


def test_contribute_results_unprocessable_is_not_retried(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 422 rejects the batch itself — an oversized batch or an
    unverifiable token — so resending it would fail identically. It is
    surfaced on the first response instead.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(
        CONTRIBUTIONS_URL,
        json={"detail": [{"msg": "Invalid id token", "type": "value_error"}]},
        status=422,
    )

    client = LinkCheckClient()
    with pytest.raises(LinkCheckContributionError):
        client.contribute_results(
            CHECK_ID,
            make_results(),
            id_token="a.b.c",
            environment=make_environment(),
        )

    assert len(responses.calls) == 1


def test_contribute_results_unreadable_body(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A 200 whose body is not a contribution report surfaces as the
    contribution's own error type rather than a `pydantic.ValidationError`.

    Ook is deployed independently of Documenteer, so a successful response
    can drift out of the shape a given release expects. The caller
    downgrades a `LinkCheckContributionError` to a warning; an escaping
    validation error would instead crash the documentation build over an
    improvement it was only trying to send.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(CONTRIBUTIONS_URL, json={"unexpected": "shape"}, status=200)

    client = LinkCheckClient()
    with pytest.raises(LinkCheckContributionError, match="ContributionReport"):
        client.contribute_results(
            CHECK_ID,
            make_results(),
            id_token="a.b.c",
            environment=make_environment(),
        )

    # A body this client cannot read reads no better on a resend, so it is
    # surfaced on the first response instead of exhausting the ladder.
    assert len(responses.calls) == 1


def test_get_check_unreadable_body(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """A check response that does not match the client's model raises a
    typed service error, which the builder degrades like any other service
    problem, rather than a `pydantic.ValidationError`.
    """
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.get(
        f"{BASE_URL}/linkcheck/checks/{CHECK_ID}",
        json={"id": CHECK_ID},
        status=200,
    )

    client = LinkCheckClient()
    with pytest.raises(LinkCheckMalformedResponseError, match="LinkCheck"):
        client.get_check(CHECK_ID)


def test_submit_check_unreadable_body(
    responses: RequestsMock, monkeypatch: Any
) -> None:
    """The submission response is read through the same guard."""
    monkeypatch.setenv("OOK_TOKEN", "test-token")
    responses.post(f"{BASE_URL}/linkcheck/checks", json=[], status=202)

    client = LinkCheckClient()
    with pytest.raises(LinkCheckMalformedResponseError):
        client.submit_check(make_request())


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


def test_oidc_audience_is_the_normalized_base_url() -> None:
    """The audience to mint an id token for is the service's own base URL,
    normalized without a trailing slash.

    The service requires the audience to be its public base URL, which is
    what scopes a token to one deployment: pointing the builder at the
    development Ook mints a token that production will not accept.
    """
    client = LinkCheckClient(base_url="https://roundtable-dev.lsst.cloud/ook/")

    assert client.oidc_audience == "https://roundtable-dev.lsst.cloud/ook"


def test_environment_from_github_actions() -> None:
    """The advisory environment block describes the workflow run, composing
    the run URL from the pieces GitHub Actions exports separately.
    """
    environment = ContributionEnvironment.from_github_actions(
        {
            "GITHUB_REPOSITORY": "lsst-sqre/documenteer",
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_RUN_ID": "42",
        }
    )

    assert environment.provider is ContributionProvider.github_actions
    assert environment.repository == "lsst-sqre/documenteer"
    assert environment.run_url == (
        "https://github.com/lsst-sqre/documenteer/actions/runs/42"
    )
    assert environment.checker_version == f"documenteer {__version__}"


def test_environment_outside_github_actions() -> None:
    """Outside GitHub Actions there is no run to describe, so the
    descriptive fields are simply empty rather than half-composed from
    whichever variables happen to be set.
    """
    environment = ContributionEnvironment.from_github_actions(
        {"GITHUB_REPOSITORY": "lsst-sqre/documenteer"}
    )

    assert environment.repository == "lsst-sqre/documenteer"
    assert environment.run_url is None
