"""A helper for minting GitHub Actions OIDC id tokens.

An id token is how a workflow run proves to a service which repository and
run it is, without a shared secret. Ook's link-check contributions endpoint
requires one as provenance for every batch of contributed results.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, NamedTuple, Self

import requests

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "REQUEST_TOKEN_ENV_VAR",
    "REQUEST_URL_ENV_VAR",
    "GitHubOidcTokenFetcher",
    "IdTokenResult",
]

REQUEST_URL_ENV_VAR = "ACTIONS_ID_TOKEN_REQUEST_URL"
"""Environment variable holding the URL of the Actions id-token endpoint."""

REQUEST_TOKEN_ENV_VAR = "ACTIONS_ID_TOKEN_REQUEST_TOKEN"
"""Environment variable holding the bearer token for the id-token
endpoint."""

_UNAVAILABLE_OUTSIDE_ACTIONS = (
    f"{REQUEST_URL_ENV_VAR} and {REQUEST_TOKEN_ENV_VAR} are not both set, so "
    "no GitHub Actions OIDC token can be minted. GitHub exports them only to "
    "a workflow job that requests the `id-token: write` permission."
)
"""Why no token is available outside a suitably-permissioned Actions job.

Worth naming the permission: the same two variables are missing whether the
build is on a laptop (nothing to fix) or in a workflow that forgot to ask
for the permission (one line to fix), and only the caller's operator can
tell those apart.
"""


class IdTokenResult(NamedTuple):
    """The outcome of requesting a GitHub Actions OIDC id token.

    A missing token is an ordinary outcome rather than an error: a build
    running outside GitHub Actions can never have one, and a contribution
    is a nice-to-have the build proceeds without. The reason travels with
    the absence so the caller can say *why* it is skipping.
    """

    token: str | None
    """The minted id token, or `None` if none could be minted."""

    unavailable_reason: str | None
    """Why no token could be minted, or `None` if one was."""

    @classmethod
    def minted(cls, token: str) -> Self:
        """Create a result for a successfully minted token."""
        return cls(token=token, unavailable_reason=None)

    @classmethod
    def unavailable(cls, reason: str) -> Self:
        """Create a result for a token that could not be minted."""
        return cls(token=None, unavailable_reason=reason)


class GitHubOidcTokenFetcher:
    """Mint GitHub Actions OIDC id tokens for a given audience.

    Parameters
    ----------
    env
        The process environment to read the Actions id-token endpoint from.
        Defaults to `os.environ`.
    session
        An existing requests session to use.
    timeout
        Timeout for the token request, in seconds.
    """

    def __init__(
        self,
        *,
        env: Mapping[str, str] | None = None,
        session: requests.Session | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._env = env if env is not None else os.environ
        self._session = session if session is not None else requests.Session()
        self._timeout = timeout

    def fetch_id_token(self, audience: str) -> IdTokenResult:
        """Mint an id token attesting to this workflow run.

        No failure here raises: every way this can come up empty — a build
        that is not a GitHub Actions job, a job without the ``id-token:
        write`` permission, an unreachable or unhappy token endpoint —
        arrives as an `IdTokenResult` carrying the reason.

        Parameters
        ----------
        audience
            The audience to mint the token for. A token is only valid for
            the audience it was minted for, which is what keeps it from
            being replayed against a different service.

        Returns
        -------
        IdTokenResult
            The minted token, or the reason no token is available.
        """
        request_url = self._env.get(REQUEST_URL_ENV_VAR)
        request_token = self._env.get(REQUEST_TOKEN_ENV_VAR)
        if not request_url or not request_token:
            return IdTokenResult.unavailable(_UNAVAILABLE_OUTSIDE_ACTIONS)
        try:
            # GitHub exports the endpoint already carrying its own query
            # (``?api-version=2.0``); requests appends the audience to it
            # rather than replacing it.
            r = self._session.get(
                request_url,
                params={"audience": audience},
                headers={"Authorization": f"Bearer {request_token}"},
                timeout=self._timeout,
            )
            r.raise_for_status()
            # requests raises a JSONDecodeError that is itself a
            # RequestException, so a non-JSON body lands in the same place
            # as a transport failure.
            payload = r.json()
        except requests.RequestException as e:
            return IdTokenResult.unavailable(
                f"the GitHub Actions OIDC token request failed: {e}"
            )
        # A 200 does not guarantee the documented ``{"value": ...}``
        # object: a proxy or an error page can answer with a JSON list or
        # string, and calling ``.get`` on that would raise where every
        # other way of coming up empty returns a reason. A body this
        # helper cannot read a token out of is simply a body with no
        # token in it.
        token = payload.get("value") if isinstance(payload, dict) else None
        if not token:
            return IdTokenResult.unavailable(
                "the GitHub Actions OIDC token request returned no token"
            )
        return IdTokenResult.minted(token)
