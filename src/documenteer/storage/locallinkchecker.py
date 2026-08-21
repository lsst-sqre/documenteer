"""A compact link checker that reproduces Sphinx linkcheck's request
semantics from the build's own vantage point.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, TypedDict

import requests
import sphinx
from pydantic import BaseModel, Field
from sphinx.builders.linkcheck import DEFAULT_REQUEST_HEADERS
from sphinx.util import requests as sphinx_requests

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DEFAULT_POLITENESS_DELAY",
    "SPHINX_REQUEST_HEADERS",
    "SPHINX_USER_AGENT",
    "LocalCheckResult",
    "LocalLinkChecker",
]

_FALLBACK_USER_AGENT = (
    f"Mozilla/5.0 (X11; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0 "
    f"Sphinx/{sphinx.__version__}"
)
"""Sphinx's default linkcheck User-Agent, reproduced verbatim for the
Sphinx releases that do not expose it as ``_USER_AGENT``."""

SPHINX_USER_AGENT: str = getattr(
    sphinx_requests, "_USER_AGENT", _FALLBACK_USER_AGENT
)
"""The User-Agent Sphinx's built-in linkcheck builder sends.

Sites that block Ook's egress typically discriminate on the User-Agent,
so a recheck is only meaningful if it presents the same browser-prefixed
identity the stock builder would. Sphinx keeps this string private
(``sphinx.util.requests._USER_AGENT``), so it is read defensively with a
verbatim fallback rather than assumed to exist.
"""

SPHINX_REQUEST_HEADERS: dict[str, str] = {
    **DEFAULT_REQUEST_HEADERS,
    "User-Agent": SPHINX_USER_AGENT,
}
"""The headers Sphinx's built-in linkcheck builder sends by default:
its ``Accept`` header plus the browser-prefixed User-Agent."""


class _RetrievalKwargs(TypedDict, total=False):
    """Per-rung keyword arguments for a retrieval attempt."""

    allow_redirects: bool
    stream: bool


_RETRIEVAL_METHODS: tuple[tuple[str, _RetrievalKwargs], ...] = (
    ("HEAD", {"allow_redirects": True}),
    ("GET", {"stream": True}),
)
"""Sphinx linkcheck's retrieval ladder: a redirect-following HEAD, then a
streamed GET if the HEAD fails (mirrors
``HyperlinkAvailabilityCheckWorker._retrieval_methods`` for the
no-anchor-checking case)."""

DEFAULT_POLITENESS_DELAY = 0.5
"""Seconds to wait between consecutive URL checks.

The checker is only ever pointed at a handful of URLs, so it trades
throughput for politeness: one request at a time, spaced out, rather than
Sphinx's thread pool.
"""


class LocalCheckResult(BaseModel):
    """One URL's observation from a local link check."""

    url: str = Field(description="The URL that was checked.")

    status_code: int | None = Field(
        None,
        description="Final HTTP status code, or null if no response arrived.",
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
        description="Description of the failure, or null if the URL resolved.",
    )

    date_checked: datetime = Field(
        description="Time the local check was performed."
    )

    @property
    def is_ok(self) -> bool:
        """Whether the URL resolved successfully from this vantage point."""
        return self.error is None


class LocalLinkChecker:
    """Check URLs locally with Sphinx linkcheck's request semantics.

    Parameters
    ----------
    timeout
        Per-request timeout, in seconds.
    delay
        Politeness delay between consecutive URL checks, in seconds.
    session
        An existing requests session to use.
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        delay: float = DEFAULT_POLITENESS_DELAY,
        session: requests.Session | None = None,
    ) -> None:
        self._timeout = timeout
        self._delay = delay
        self._session = session if session is not None else requests.Session()

    def check_urls(self, urls: Sequence[str]) -> list[LocalCheckResult]:
        """Check each URL in turn, in the order given.

        The checks are sequential with a politeness delay between them
        (never before the first), so a handful of rechecks never arrives
        at a site as a burst.

        Parameters
        ----------
        urls
            The URLs to check.

        Returns
        -------
        list of LocalCheckResult
            One observation per URL, in the order the URLs were given.
        """
        results: list[LocalCheckResult] = []
        for index, url in enumerate(urls):
            if index > 0 and self._delay > 0:
                time.sleep(self._delay)
            results.append(self.check_url(url))
        return results

    def check_url(self, url: str) -> LocalCheckResult:
        """Check one URL and record what this vantage point observed.

        The retrieval ladder mirrors Sphinx's built-in linkcheck builder:
        a HEAD that follows redirects, falling back to a streamed GET
        when the HEAD fails (many servers reject HEAD outright or drop
        the connection on it).
        """
        status_code: int | None = None
        redirect_status_code: int | None = None
        redirect_url: str | None = None
        error = ""
        for method, kwargs in _RETRIEVAL_METHODS:
            try:
                with self._session.request(
                    method,
                    url,
                    headers=SPHINX_REQUEST_HEADERS,
                    timeout=self._timeout,
                    **kwargs,
                ) as response:
                    # Recorded before raise_for_status so a failing
                    # response still leaves its evidence behind, and left
                    # in place across a fallback attempt so a connection
                    # error on the GET does not erase the HEAD's response
                    # (this mirrors Sphinx's own bookkeeping).
                    status_code = response.status_code
                    if response.history:
                        redirect_status_code = response.history[-1].status_code
                        redirect_url = response.url
                    response.raise_for_status()
            except requests.RequestException as e:
                error = str(e)
            else:
                # This retrieval method resolved the URL; discard any
                # error the earlier method in the ladder recorded.
                error = ""
                break
        return LocalCheckResult(
            url=url,
            status_code=status_code,
            redirect_status_code=redirect_status_code,
            redirect_url=redirect_url,
            error=error or None,
            date_checked=datetime.now(tz=UTC),
        )
