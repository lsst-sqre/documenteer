"""Client for Ook's link-check service API."""

from __future__ import annotations

import os
import time
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, NamedTuple, Self

import requests
from pydantic import BaseModel, Field, ValidationError

from documenteer._requestsutils import requests_retry_session

from ..version import __version__

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "DEFAULT_BASE_URL",
    "TOKEN_ENV_VAR",
    "AcceptedContribution",
    "CheckRunStatus",
    "CheckUrlStatus",
    "CheckedUrl",
    "ContributedResult",
    "ContributionEnvironment",
    "ContributionProvenance",
    "ContributionProvider",
    "ContributionRejectionReason",
    "ContributionReport",
    "LinkCheck",
    "LinkCheckClient",
    "LinkCheckContributionError",
    "LinkCheckContributionRequest",
    "LinkCheckHttpError",
    "LinkCheckMalformedResponseError",
    "LinkCheckRequest",
    "LinkCheckServiceError",
    "LinkCheckSummary",
    "LinkCheckTimeoutError",
    "LinkCheckUnauthorizedError",
    "LinkCheckUnreachableError",
    "RejectedContribution",
    "SubmittedCheck",
    "SubmittedUrl",
]

DEFAULT_BASE_URL = "https://roundtable.lsst.cloud/ook"
"""Production base URL for the Ook API."""

TOKEN_ENV_VAR = "OOK_TOKEN"
"""Environment variable holding the bearer token for the Ook API."""

_CONTRIBUTION_RETRIES = 3
"""How many times a contribution POST is resent after a retryable failure
before it is given up on."""

_CONTRIBUTION_INITIAL_BACKOFF = 0.5
"""Seconds to wait before the first contribution retry; the wait doubles
with each further retry."""

_CONTRIBUTION_RETRY_STATUS_CODES = frozenset({502})
"""Response status codes that make a contribution worth resending.

The service answers with a 502 when it could not fetch GitHub's OIDC
signing keys to verify the id token — a failure in a third service, which
it documents as retryable.
"""


class LinkCheckServiceError(ValueError):
    """An error interacting with Ook's link-check service."""


class LinkCheckUnreachableError(LinkCheckServiceError):
    """The Ook link-check service could not be reached."""


class LinkCheckUnauthorizedError(LinkCheckServiceError):
    """The request to the Ook link-check service was not authorized."""


class LinkCheckTimeoutError(LinkCheckServiceError):
    """The link check did not complete within the polling budget."""


class LinkCheckHttpError(LinkCheckServiceError):
    """An error response from the Ook link-check service.

    Carries the response's status code so a caller can tell a failure
    worth retrying from one that will fail the same way every time.
    """

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
        """The HTTP status code the service responded with."""


class LinkCheckContributionError(LinkCheckServiceError):
    """A batch of contributed results could not be delivered.

    Raised as its own type because a contribution is optional: the caller
    downgrades this to a warning and reports the check it already has,
    rather than failing a build over an improvement it could not send.
    """


class LinkCheckMalformedResponseError(LinkCheckServiceError):
    """The service answered successfully with a body this client could
    not parse.

    Ook is deployed independently of Documenteer, so a response can drift
    out of the shape a given Documenteer release expects. That is a
    service problem like any other — it belongs in this error hierarchy,
    where the builder already degrades it to a warning — rather than a
    `pydantic.ValidationError` escaping into a documentation build as an
    unhandled traceback.
    """


def _parse_response[M: BaseModel](model: type[M], r: requests.Response) -> M:
    """Validate a successful response's body into one of this client's
    models.

    Parameters
    ----------
    model
        The model the body is expected to conform to.
    r
        The response whose body is being read.

    Returns
    -------
    pydantic.BaseModel
        The parsed model.

    Raises
    ------
    LinkCheckMalformedResponseError
        Raised if the body does not match ``model``.
    """
    try:
        return model.model_validate_json(r.text)
    except ValidationError as e:
        raise LinkCheckMalformedResponseError(
            f"The Ook link-check service at {r.url} answered HTTP "
            f"{r.status_code} with a body this Documenteer release could "
            f"not read as {model.__name__}: {e}"
        ) from e


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
    blocked = "blocked"


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

    blocked: int = Field(
        0,
        description=(
            "URLs blocked by bot protection, unverifiable from CI's vantage "
            "point (not counted as broken)."
        ),
    )


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

    origin_paths: list[str] = Field(
        default_factory=list,
        description=(
            "Page paths where the URL occurs, echoed back from the "
            "submission, relative to the origin's base URL. Defaults to an "
            "empty list when the field is absent, tolerating an Ook that "
            "does not yet report it."
        ),
    )


class LinkCheck(BaseModel):
    """A submitted link check with its per-URL results."""

    id: str = Field(
        description=(
            "The check's identifier, an opaque Ook Crockford base32 token "
            "(e.g. ``a1b2-c3d4-e5f6-g7h8``). Treated as an opaque string; "
            "it is never parsed or validated as a number."
        )
    )

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


class ContributionProvider(StrEnum):
    """The kind of client environment a contribution was observed from."""

    github_actions = "github_actions"


class ContributionRejectionReason(StrEnum):
    """Why one contributed result was not applied to its URL."""

    not_a_member = "not_a_member"
    """The URL is not one of the check's member URLs."""

    not_blocked = "not_blocked"
    """The URL's status is not ``blocked``, so Ook's own vantage point
    already settled it."""

    unsupported_url = "unsupported_url"
    """The URL is not a checkable http(s) URL."""

    duplicate = "duplicate"
    """An earlier entry in the same batch already contributed a result for
    this URL."""


class ContributionEnvironment(BaseModel):
    """The client environment a batch of contributed results came from.

    Every field here is advisory. The repository a contribution is recorded
    under comes from the verified id token, never from this block; these
    fields are recorded for display in the service's reports.
    """

    provider: ContributionProvider = Field(
        ContributionProvider.github_actions,
        description=(
            "The kind of client environment the results were observed "
            "from. Only GitHub Actions runs can contribute, because the "
            "provenance attestation is an Actions OIDC id token."
        ),
    )

    repository: str | None = Field(
        None,
        description=(
            "The ``owner/name`` of the repository the client believes it is "
            "running in."
        ),
    )

    run_url: str | None = Field(
        None, description="URL of the workflow run that observed the results."
    )

    checker_version: str | None = Field(
        None, description="Version of the client that performed the checks."
    )

    @classmethod
    def from_github_actions(cls, env: Mapping[str, str] | None = None) -> Self:
        """Describe the current GitHub Actions run.

        Parameters
        ----------
        env
            The process environment to read the run's identity from.
            Defaults to `os.environ`.

        Returns
        -------
        ContributionEnvironment
            The advisory environment block, with whatever of the run's
            identity the environment supplies. Outside GitHub Actions the
            descriptive fields are simply empty; the block still names this
            client's version, and the service ignores the rest in favor of
            the id token's claims regardless.
        """
        env = env if env is not None else os.environ
        repository = env.get("GITHUB_REPOSITORY")
        server_url = env.get("GITHUB_SERVER_URL")
        run_id = env.get("GITHUB_RUN_ID")
        run_url = (
            f"{server_url.rstrip('/')}/{repository}/actions/runs/{run_id}"
            if server_url and repository and run_id
            else None
        )
        return cls(
            provider=ContributionProvider.github_actions,
            repository=repository,
            run_url=run_url,
            checker_version=f"documenteer {__version__}",
        )


class ContributedResult(BaseModel):
    """One URL's result as observed by the contributing client."""

    url: str = Field(description="The URL the client checked.")

    status_code: int | None = Field(
        None,
        description=(
            "Final HTTP status code the client received, or null if it "
            "received no response at all."
        ),
    )

    redirect_status_code: int | None = Field(
        None,
        description=(
            "HTTP status code of the redirect (e.g. 301, 302), if the URL "
            "redirected."
        ),
    )

    redirect_url: str | None = Field(
        None, description="Final resolved location, if the URL redirected."
    )

    error: str | None = Field(
        None,
        description=(
            "Description of the failure, if the client's check failed."
        ),
    )

    checked_at: datetime = Field(
        description="Time the client performed the check."
    )


class LinkCheckContributionRequest(BaseModel):
    """The submission payload for a batch of contributed results."""

    id_token: str = Field(
        description=(
            "A GitHub Actions OIDC id token, minted for the deployment's "
            "audience by the workflow run that observed the results. Its "
            "claims are what the contribution is recorded under."
        )
    )

    environment: ContributionEnvironment = Field(
        description="The client environment the results came from."
    )

    results: list[ContributedResult] = Field(
        description="The per-URL results the client observed."
    )


class ContributionProvenance(BaseModel):
    """Where the service recorded a batch of results as coming from."""

    provider: ContributionProvider = Field(
        description="The kind of client environment."
    )

    repository: str = Field(
        description=(
            "The ``owner/name`` of the repository whose CI observed the "
            "results, from the verified id token."
        )
    )

    run_id: str = Field(
        description=(
            "The workflow run that observed the results, from the verified "
            "id token."
        )
    )

    workflow_ref: str = Field(
        description=(
            "The fully-qualified reference of the workflow that observed "
            "the results, from the verified id token."
        )
    )

    run_url: str | None = Field(
        None, description="The run URL the client reported, if any."
    )

    checker_version: str | None = Field(
        None, description="The client version the client reported, if any."
    )


class AcceptedContribution(BaseModel):
    """A contributed result that was applied to its URL."""

    url: str = Field(description="The canonical URL the result applied to.")

    status: CheckUrlStatus = Field(
        description=(
            "The URL's status after the contributed result ran through the "
            "service's status-transition engine."
        )
    )


class RejectedContribution(BaseModel):
    """A contributed result that was not applied, and why."""

    url: str = Field(description="The URL as it was submitted.")

    reason: ContributionRejectionReason | str = Field(
        description="Why the result was not applied.",
        union_mode="left_to_right",
    )

    message: str = Field(
        description="A human-readable explanation of the rejection."
    )


class ContributionReport(BaseModel):
    """The outcome of a batch of contributed results.

    The service applies a batch entry by entry, so a report can carry both
    accepted and rejected entries: an entry the service declines does not
    cost the rest of the batch.
    """

    check_id: str = Field(
        description="The check the results were contributed against."
    )

    provenance: ContributionProvenance = Field(
        description=(
            "Where the results were recorded as coming from, taken from the "
            "verified id token."
        )
    )

    accepted: list[AcceptedContribution] = Field(
        default_factory=list,
        description=(
            "The results that were applied, with the status each URL "
            "reached, in submission order."
        ),
    )

    rejected: list[RejectedContribution] = Field(
        default_factory=list,
        description=(
            "The results that were not applied, each with its reason, in "
            "submission order."
        ),
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

    @property
    def oidc_audience(self) -> str:
        """The audience an OIDC id token must be minted for to attest to a
        contribution to this service.

        The service requires the audience to be its own public base URL,
        which is what scopes a minted token to one deployment: a token
        minted for the development Ook is not replayable against
        production. This is the configured service URL normalized without
        a trailing slash.
        """
        return self._base_url

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
        check = _parse_response(LinkCheck, r)
        poll_url = r.headers.get("Location") or check.self_url
        return SubmittedCheck(check=check, poll_url=poll_url)

    def get_check(self, check_id: str) -> LinkCheck:
        """Get a link check by its identifier.

        Parameters
        ----------
        check_id
            Identifier of the link check, from `LinkCheck.id`. An opaque
            token that is interpolated into the resource URL as-is, never
            parsed as a number.

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

    def contribute_results(
        self,
        check_id: str,
        results: Sequence[ContributedResult],
        *,
        id_token: str,
        environment: ContributionEnvironment,
    ) -> ContributionReport:
        """Contribute locally-observed results for a check's blocked URLs.

        Parameters
        ----------
        check_id
            Identifier of the link check the results belong to.
        results
            The per-URL observations to contribute.
        id_token
            A GitHub Actions OIDC id token minted for this service's
            `oidc_audience`, from
            `~documenteer.storage.githuboidc.GitHubOidcTokenFetcher`. It
            attests to where the results were observed, and the service
            records its claims as the contribution's provenance.
        environment
            The advisory description of the client environment.

        Returns
        -------
        ContributionReport
            What the service did with each result: the entries it applied
            and the entries it declined, each with a reason.

        Raises
        ------
        LinkCheckContributionError
            Raised if the contribution could not be delivered, including
            when the retryable failures below outlast the retry ladder,
            and if the service answers with a body this client cannot
            read as a `ContributionReport`.

        Notes
        -----
        The service answers a request it could not verify against GitHub's
        signing keys with a 502, which it documents as worth retrying, so
        that and a connection failure are resent up to
        `_CONTRIBUTION_RETRIES` times on a doubling backoff. Anything else
        — a 422 for a malformed batch or an unverifiable token, say — will
        fail identically however many times it is sent, so it is surfaced
        immediately.
        """
        url = f"{self._base_url}/linkcheck/checks/{check_id}/contributions"
        request = LinkCheckContributionRequest(
            id_token=id_token,
            environment=environment,
            results=list(results),
        )
        payload = request.model_dump(mode="json")
        backoff = _CONTRIBUTION_INITIAL_BACKOFF
        attempts = _CONTRIBUTION_RETRIES + 1
        last_error: LinkCheckServiceError
        for attempt in range(1, attempts + 1):
            try:
                r = self._request("POST", url, json_payload=payload)
            except LinkCheckUnreachableError as e:
                last_error = e
            except LinkCheckHttpError as e:
                if e.status_code not in _CONTRIBUTION_RETRY_STATUS_CODES:
                    raise LinkCheckContributionError(
                        f"Could not contribute link-check results: {e}"
                    ) from e
                last_error = e
            else:
                try:
                    return _parse_response(ContributionReport, r)
                except LinkCheckMalformedResponseError as e:
                    # A body this client cannot read will read no better
                    # on a resend, so it is surfaced immediately — as the
                    # contribution's own error type, which is what the
                    # caller downgrades to a warning.
                    raise LinkCheckContributionError(
                        f"Could not contribute link-check results: {e}"
                    ) from e
            if attempt < attempts:
                time.sleep(backoff)
                backoff *= 2.0
        raise LinkCheckContributionError(
            f"Could not contribute link-check results after {attempts} "
            f"attempts: {last_error}"
        ) from last_error

    def _get_check(self, url: str) -> LinkCheck:
        """Get a link check at its API URL."""
        r = self._request("GET", url)
        return _parse_response(LinkCheck, r)

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
            raise LinkCheckHttpError(
                f"Error from the Ook link-check service at {url}: {e}",
                status_code=r.status_code,
            ) from e
        return r
