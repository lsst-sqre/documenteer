"""Tests for the GitHub Actions OIDC id-token helper."""

from __future__ import annotations

import pytest_responses  # noqa: F401
from requests.exceptions import ConnectionError as RequestsConnectionError
from responses import RequestsMock

from documenteer.storage.githuboidc import GitHubOidcTokenFetcher

TOKEN_ENDPOINT = "https://token.actions.githubusercontent.com/req"
"""The Actions id-token endpoint, as ``responses`` registers it.

Registered without a query string so ``responses`` ignores the request's
own query when matching, leaving the tests free to assert on it.
"""

TOKEN_REQUEST_URL = f"{TOKEN_ENDPOINT}?api-version=2.0"
"""The endpoint as GitHub Actions exports it: already query-bearing."""

ACTIONS_ENV = {
    "ACTIONS_ID_TOKEN_REQUEST_URL": TOKEN_REQUEST_URL,
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "request-token",
}
"""The environment a workflow job with ``id-token: write`` is given."""


def test_fetch_id_token(responses: RequestsMock) -> None:
    """The fetcher mints an id token from the Actions token endpoint,
    presenting the request token as bearer auth and asking for the caller's
    audience.
    """
    responses.get(TOKEN_ENDPOINT, json={"value": "a.b.c"}, status=200)

    result = GitHubOidcTokenFetcher(env=ACTIONS_ENV).fetch_id_token(
        "https://roundtable.lsst.cloud/ook"
    )

    assert result.token == "a.b.c"
    assert result.unavailable_reason is None
    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bearer request-token"
    assert request.url is not None
    # The audience is added to the query GitHub already put on the
    # endpoint, not in place of it.
    assert "audience=https%3A%2F%2Froundtable.lsst.cloud%2Fook" in request.url
    assert "api-version=2.0" in request.url


def test_outside_github_actions(responses: RequestsMock) -> None:
    """Without the Actions id-token environment variables there is nothing
    to ask, so the fetcher reports the environment as unavailable — naming
    the permission that supplies them — rather than raising or making a
    doomed request.
    """
    result = GitHubOidcTokenFetcher(env={}).fetch_id_token(
        "https://roundtable.lsst.cloud/ook"
    )

    assert result.token is None
    assert result.unavailable_reason is not None
    assert "id-token: write" in result.unavailable_reason
    assert len(responses.calls) == 0


def test_token_request_fails(responses: RequestsMock) -> None:
    """A token endpoint that answers with an error is reported as an
    unavailable token, not raised: nothing the caller can do about it
    should cost it the rest of its work.
    """
    responses.get(TOKEN_ENDPOINT, json={"message": "no"}, status=403)

    result = GitHubOidcTokenFetcher(env=ACTIONS_ENV).fetch_id_token(
        "https://roundtable.lsst.cloud/ook"
    )

    assert result.token is None
    assert result.unavailable_reason is not None
    assert "403" in result.unavailable_reason


def test_token_endpoint_unreachable(responses: RequestsMock) -> None:
    """A token endpoint that cannot be reached at all is reported the same
    way: an unavailable token carrying the transport error as its reason.
    """
    responses.get(TOKEN_ENDPOINT, body=RequestsConnectionError("no route"))

    result = GitHubOidcTokenFetcher(env=ACTIONS_ENV).fetch_id_token(
        "https://roundtable.lsst.cloud/ook"
    )

    assert result.token is None
    assert result.unavailable_reason is not None
    assert "no route" in result.unavailable_reason


def test_token_response_without_value(responses: RequestsMock) -> None:
    """A 200 response that carries no token is not a token: the fetcher
    reports it as unavailable rather than passing an empty string on to be
    rejected by the service.
    """
    responses.get(TOKEN_ENDPOINT, json={"count": 1}, status=200)

    result = GitHubOidcTokenFetcher(env=ACTIONS_ENV).fetch_id_token(
        "https://roundtable.lsst.cloud/ook"
    )

    assert result.token is None
    assert result.unavailable_reason is not None
