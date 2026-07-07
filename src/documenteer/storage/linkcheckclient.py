"""Client for Ook's link-check service API."""

from __future__ import annotations

import os
import time
from datetime import datetime
from enum import StrEnum
from typing import NamedTuple

import requests
from pydantic import BaseModel, Field

from documenteer._requestsutils import requests_retry_session

__all__ = [
    "DEFAULT_BASE_URL",
    "TOKEN_ENV_VAR",
    "CheckRunStatus",
    "CheckUrlStatus",
    "CheckedUrl",
    "LinkCheck",
    "LinkCheckClient",
    "LinkCheckRequest",
    "LinkCheckServiceError",
    "LinkCheckSummary",
    "LinkCheckTimeoutError",
    "LinkCheckUnauthorizedError",
    "LinkCheckUnreachableError",
    "SubmittedCheck",
    "SubmittedUrl",
]

DEFAULT_BASE_URL = "https://roundtable.lsst.cloud/ook"
"""Production base URL for the Ook API."""

TOKEN_ENV_VAR = "OOK_TOKEN"
"""Environment variable holding the bearer token for the Ook API."""


class LinkCheckServiceError(ValueError):
    """An error interacting with Ook's link-check service."""


class LinkCheckUnreachableError(LinkCheckServiceError):
    """The Ook link-check service could not be reached."""


class LinkCheckUnauthorizedError(LinkCheckServiceError):
    """The request to the Ook link-check service was not authorized."""


class LinkCheckTimeoutError(LinkCheckServiceError):
    """The link check did not complete within the polling budget."""


class CheckRunStatus(StrEnum):
    """The processing status of a submitted link check."""

    pending = "pending"
    in_progress = "in_progress"
    complete = "complete"


class CheckUrlStatus(StrEnum):
    """The reported status of a URL within a submitted link check."""

    pending = "pending"
    ok = "ok"
    redirected = "redirected"
    failing = "failing"
    broken = "broken"
    unsupported = "unsupported"


class SubmittedUrl(BaseModel):
    """A URL submitted for checking, with the pages it occurs on."""

    url: str = Field(description="The URL to check.")

    origin_paths: list[str] = Field(
        default_factory=list,
        description=(
            "Page paths where the URL occurs, relative to the origin's "
            "base URL."
        ),
    )


class LinkCheckRequest(BaseModel):
    """The submission payload for a link check."""

    origin_base_url: str = Field(
        description=(
            "The base URL of the website the submission is for (e.g. "
            "https://documenteer.lsst.io). Must be an absolute http(s) URL "
            "without a query or fragment; path-bearing bases are allowed. "
            "The service normalizes it by lowercasing the host and "
            "stripping any trailing slash."
        )
    )

    is_default_version: bool = Field(
        description=(
            "Whether the submission is a build of the origin's default "
            "version. Only default-version submissions replace the origin's "
            "recorded URL occurrences."
        )
    )

    urls: list[SubmittedUrl] = Field(description="The URLs to check.")


class LinkCheckSummary(BaseModel):
    """Counts of a link check's URLs by status."""

    pending: int = Field(0, description="URLs awaiting a check.")

    ok: int = Field(0, description="URLs that resolve successfully.")

    redirected: int = Field(
        0, description="URLs that work via a permanent redirect."
    )

    failing: int = Field(
        0, description="URLs currently failing (retry in progress)."
    )

    broken: int = Field(0, description="Broken URLs.")

    unsupported: int = Field(0, description="URLs that cannot be checked.")


class CheckedUrl(BaseModel):
    """The result for one URL within a link check."""

    url: str = Field(description="The canonical (fragment-stripped) URL.")

    status: CheckUrlStatus = Field(description="The URL's status.")

    status_code: int | None = Field(
        None,
        description="Final HTTP status code, if a response was received.",
    )

    redirect_status_code: int | None = Field(
        None,
        description=(
            "HTTP status code of the redirect (e.g. 301, 302), if the URL "
            "redirected."
        ),
    )

    redirect_url: str | None = Field(
        None,
        description="Final resolved location, if the URL redirected.",
    )

    error: str | None = Field(
        None,
        description="Description of the failure, if the check failed.",
    )

    checked_at: datetime | None = Field(
        None,
        description=(
            "Time of the check that produced this result, or null while the "
            "URL is pending."
        ),
    )


class LinkCheck(BaseModel):
    """A submitted link check with its per-URL results."""

    id: int = Field(description="The check's identifier.")

    self_url: str = Field(description="URL to access this check in the API.")

    origin_base_url: str = Field(
        description=(
            "The normalized base URL of the origin website the check was "
            "submitted for."
        )
    )

    is_default_version: bool = Field(
        description=(
            "Whether the submission is a build of the origin's default "
            "version."
        )
    )

    status: CheckRunStatus = Field(
        description="The processing status of the check."
    )

    date_created: datetime = Field(description="Time the check was submitted.")

    date_completed: datetime | None = Field(
        None,
        description="Time the check completed, or null while unfinished.",
    )

    summary: LinkCheckSummary = Field(
        description="Counts of the check's URLs by status."
    )

    urls: list[CheckedUrl] = Field(
        description="Per-URL results, ordered by URL."
    )


class SubmittedCheck(NamedTuple):
    """The outcome of submitting a link check to the service."""

    check: LinkCheck
    """The created link check, parsed from the submission response body."""

    poll_url: str
    """URL to poll the check at, from the ``Location`` header (or the
    check's ``self_url`` if the header is absent).
    """


class LinkCheckClient:
    """A client for Ook's link-check service API.

    Parameters
    ----------
    base_url
        Base URL of the Ook API. Defaults to the production Ook API,
        `DEFAULT_BASE_URL`.
    token
        Bearer token for the Ook API. If not provided, the token is read
        from the ``OOK_TOKEN`` environment variable.
    session
        An existing requests session to use. By default a session with
        retries is created with
        `documenteer._requestsutils.requests_retry_session`.
    """

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        token: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token if token is not None else os.getenv(TOKEN_ENV_VAR)
        self._session = (
            session if session is not None else requests_retry_session()
        )

    def submit_check(self, request: LinkCheckRequest) -> SubmittedCheck:
        """Submit a link check to the service.

        Parameters
        ----------
        request
            The link-check submission.

        Returns
        -------
        SubmittedCheck
            The created link check and the URL to poll it at. The service
            returns the check resource as the response body for both a
            200 (completed at submission: every URL resolved immediately,
            so the results are already in the body) and a 202 (accepted
            with URLs still to resolve: poll at ``poll_url`` with
            `poll_check` until the check's ``status`` is ``complete``).
        """
        url = f"{self._base_url}/linkcheck/checks"
        r = self._request("POST", url, json_payload=request.model_dump())
        check = LinkCheck.model_validate_json(r.text)
        poll_url = r.headers.get("Location") or check.self_url
        return SubmittedCheck(check=check, poll_url=poll_url)

    def get_check(self, check_id: int) -> LinkCheck:
        """Get a link check by its identifier.

        Parameters
        ----------
        check_id
            Identifier of the link check, from `LinkCheck.id`.

        Returns
        -------
        LinkCheck
            The link check with its current status and per-URL results.
        """
        return self._get_check(f"{self._base_url}/linkcheck/checks/{check_id}")

    def poll_check(
        self,
        poll_url: str,
        *,
        budget: float = 300.0,
        initial_interval: float = 1.0,
        max_interval: float = 30.0,
    ) -> LinkCheck:
        """Poll a link check with backoff until it completes.

        Parameters
        ----------
        poll_url
            URL of the link check in the API, from
            `SubmittedCheck.poll_url` (the submission's ``Location``
            header, falling back to the check's ``self_url``).
        budget
            Maximum time to wait for the check to complete, in seconds.
        initial_interval
            Initial delay between polls, in seconds. The delay doubles
            after each poll, up to ``max_interval``.
        max_interval
            Maximum delay between polls, in seconds.

        Returns
        -------
        LinkCheck
            The completed link check.

        Raises
        ------
        LinkCheckTimeoutError
            Raised if the check does not complete within ``budget``
            seconds.
        """
        deadline = time.monotonic() + budget
        interval = initial_interval
        while True:
            check = self._get_check(poll_url)
            if check.status is CheckRunStatus.complete:
                return check
            if time.monotonic() + interval > deadline:
                raise LinkCheckTimeoutError(
                    f"The Ook link check at {poll_url} did not complete "
                    f"within the {budget} second polling budget."
                )
            time.sleep(interval)
            interval = min(interval * 2.0, max_interval)

    def _get_check(self, url: str) -> LinkCheck:
        """Get a link check at its API URL."""
        r = self._request("GET", url)
        return LinkCheck.model_validate_json(r.text)

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_payload: dict | None = None,
    ) -> requests.Response:
        if not self._token:
            raise LinkCheckUnauthorizedError(
                "No Ook API token is available. Set the "
                f"{TOKEN_ENV_VAR} environment variable."
            )
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            r = self._session.request(
                method,
                url,
                headers=headers,
                json=json_payload,
                timeout=30.0,
            )
        except requests.RequestException as e:
            raise LinkCheckUnreachableError(
                f"Could not reach the Ook link-check service at {url}: {e}"
            ) from e
        if r.status_code in (401, 403):
            raise LinkCheckUnauthorizedError(
                f"Not authorized to access the Ook link-check service at "
                f"{url} (HTTP {r.status_code}). Check the {TOKEN_ENV_VAR} "
                "environment variable."
            )
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            raise LinkCheckServiceError(
                f"Error from the Ook link-check service at {url}: {e}"
            ) from e
        return r
